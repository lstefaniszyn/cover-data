"""End-to-end geometry orchestration: fragments and candidate rule lines in,
a reconstructed `Document` out (plan.md Phase 5).

Pure over already-detected primitives -- OCR and pixel-level line detection
are the caller's job (`ocr.engine`, `geometry.lines`); this module only
composes the row strategy, multi-table segmentation, column resolution and
cell assignment already built for this phase.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise
from statistics import median

from cover_data.domain import Document, OcrFragment, Table
from cover_data.geometry.columns import build_column_bands, extend_last_column_to_edge
from cover_data.geometry.lines import LineSegment
from cover_data.geometry.rows_ruled import (
    RowBand,
    build_ruled_row_bands,
    extend_band_bottom_to_edge,
)
from cover_data.geometry.strategy import select_row_strategy
from cover_data.geometry.table import build_table, segment_row_bands_by_gap

# A page-edge closing rule is expected within this fraction of the page
# dimension; anything short of it is treated as "no closing rule found"
# rather than a rule that merely fell slightly short of detection.
_EDGE_TOLERANCE_FRAC = 0.02


def _center(fragment: OcrFragment) -> tuple[float, float]:
    bbox = fragment.bbox
    return (bbox.x_min + bbox.x_max) / 2.0, (bbox.y_min + bbox.y_max) / 2.0


def _fragments_in_band(
    fragments: Sequence[OcrFragment], band: RowBand
) -> list[OcrFragment]:
    result = []
    for fragment in fragments:
        x, y = _center(fragment)
        if band.top.y_at(x) <= y < band.bottom.y_at(x):
            result.append(fragment)
    return result


def _maybe_extend_last_row_to_edge(
    bands: list[RowBand],
    fragments: Sequence[OcrFragment],
    column_left: float,
    column_right: float,
    page_height: float,
) -> list[RowBand]:
    """Row extent under an unclosed table must reach the page edge
    (`18.png`'s bottom-truncated row 23), never detected content extent --
    but content genuinely unrelated to the table (`26.png`'s sign-off
    block) must not be swallowed as a phantom row. The discriminator: a
    truncated row still has fragments spread across the table's own column
    grid, immediately below the last band; free-floating sign-off ink does
    not reliably fill it the same way, so this only fires when enough of
    the grid is occupied close to the last rule."""
    if not bands:
        return bands
    last = bands[-1]
    last_bottom = last.bottom.y_at((column_left + column_right) / 2.0)
    if last_bottom >= page_height - _EDGE_TOLERANCE_FRAC * page_height:
        return bands

    median_height = median(b.bottom.y_at(0.0) - b.top.y_at(0.0) for b in bands)
    nearby = [
        f
        for f in fragments
        if column_left <= _center(f)[0] < column_right
        and last_bottom <= _center(f)[1] < last_bottom + 2.0 * median_height
    ]
    if len(nearby) < 2:
        return bands

    extended = extend_band_bottom_to_edge(last, edge_y=page_height)
    return [*bands[:-1], extended]


def _cluster_lines_by_gap(
    lines: Sequence[LineSegment], gap_frac: float
) -> list[list[LineSegment]]:
    """Group rule lines by vertical gap before they are paired into bands
    -- pairing every consecutive rule across the *entire* page first (as
    `build_ruled_row_bands` does) would fold a genuine inter-table gap
    (`23.png`) into one oversized band, hiding it from a later
    band-to-band gap check rather than exposing it."""
    if not lines:
        return []
    ordered = sorted(lines, key=lambda ln: (ln.y0 + ln.y1) / 2.0)
    if len(ordered) < 3:
        return [ordered]

    ys = [(ln.y0 + ln.y1) / 2.0 for ln in ordered]
    gaps = [b - a for a, b in pairwise(ys)]
    threshold = max(gap_frac * median(gaps), 1e-6)

    groups = [[ordered[0]]]
    for line, gap in zip(ordered[1:], gaps, strict=True):
        if gap > threshold:
            groups.append([])
        groups[-1].append(line)
    return groups


def reconstruct_document(
    fragments: Sequence[OcrFragment],
    horizontal_lines: Sequence[LineSegment],
    vertical_lines: Sequence[LineSegment],
    page_width: float,
    page_height: float,
    row_gap_frac: float = 2.0,
) -> tuple[Document, tuple[OcrFragment, ...], bool]:
    """Returns the reconstructed `Document`, every fragment that landed in
    no cell of any table, and whether the document was reconstructed by
    the borderless strategy (a property of the result, per plan.md
    "Strategy selection")."""
    strategy = select_row_strategy(horizontal_lines, fragments, page_width, page_height)

    if strategy.borderless:
        groups = segment_row_bands_by_gap(list(strategy.bands), gap_frac=row_gap_frac)
    else:
        line_groups = _cluster_lines_by_gap(horizontal_lines, gap_frac=row_gap_frac)
        groups = [
            bands
            for bands in (
                build_ruled_row_bands(g, page_height=page_height) for g in line_groups
            )
            if bands
        ]

    tables: list[Table] = []
    unassigned: list[OcrFragment] = []

    for table_index, group in enumerate(groups):
        if not group:
            continue
        header_band, *data_bands = group

        group_top = min(b.top.y_at(0.0) for b in group)
        group_bottom = max(b.bottom.y_at(page_width) for b in group)
        local_verticals = [
            ln
            for ln in vertical_lines
            if not (max(ln.y0, ln.y1) < group_top or min(ln.y0, ln.y1) > group_bottom)
        ]
        header_fragments = _fragments_in_band(fragments, header_band)
        column_bands = build_column_bands(local_verticals, header_fragments, page_width)
        if column_bands and column_bands[-1].right < page_width * (
            1.0 - _EDGE_TOLERANCE_FRAC
        ):
            column_bands = extend_last_column_to_edge(column_bands, edge_x=page_width)

        if column_bands and data_bands:
            data_bands = _maybe_extend_last_row_to_edge(
                data_bands,
                fragments,
                column_left=column_bands[0].left,
                column_right=column_bands[-1].right,
                page_height=page_height,
            )

        header_ids = {id(f) for f in header_fragments}
        table_fragments = [f for f in fragments if id(f) not in header_ids]
        table, table_unassigned = build_table(
            data_bands, column_bands, table_fragments, table_index
        )
        tables.append(table)
        unassigned.extend(table_unassigned)

    return Document(tables=tuple(tables)), tuple(unassigned), strategy.borderless
