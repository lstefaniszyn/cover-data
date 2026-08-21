"""Borderless row strategy: recover rows from fragment positions alone, no
ruling lines required (plan.md Phase 5, "Borderless row strategy").

`16.png` has no rules at all and its `must` requires rows to be recovered
"from text clustering, not ruling lines" -- a supported fixture, so this
path is a peer of the ruled strategy, not a degraded fallback. Non-table
ink (`25.png`'s in-cell signature, `22.png`'s stamp) is why the baseline
fit uses a robust estimator rather than fitting to every fragment in a
candidate row.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise
from statistics import median

from cover_data.domain import OcrFragment, Point
from cover_data.geometry.rows_ruled import Curve, RowBand

# How large a gap between vertically-sorted fragment centers, relative to
# the median fragment height, counts as "next row" rather than "same row".
_DEFAULT_GAP_FRAC = 0.6


def _fragment_center_y(fragment: OcrFragment) -> float:
    bbox = fragment.bbox
    return (bbox.y_min + bbox.y_max) / 2.0


def cluster_fragments_into_rows(
    fragments: Sequence[OcrFragment], gap_frac: float = _DEFAULT_GAP_FRAC
) -> list[tuple[OcrFragment, ...]]:
    """Group fragments into rows by vertical position: sort by vertical
    center, then split wherever the gap to the next fragment exceeds
    `gap_frac` of the median fragment height. A small stray fragment (a
    signature, a stamp) whose center still falls within the surrounding
    row's gap tolerance stays in that row rather than starting a new one."""
    if not fragments:
        return []

    heights = [f.bbox.y_max - f.bbox.y_min for f in fragments]
    threshold = max(gap_frac * median(heights), 1e-6)

    ordered = sorted(fragments, key=_fragment_center_y)
    rows: list[list[OcrFragment]] = [[ordered[0]]]
    for prev, current in pairwise(ordered):
        if _fragment_center_y(current) - _fragment_center_y(prev) > threshold:
            rows.append([])
        rows[-1].append(current)
    return [tuple(row) for row in rows]


def fit_row_baselines(
    rows: Sequence[Sequence[OcrFragment]], page_width: float
) -> list[Curve]:
    """One flat baseline per row, at the *median* vertical center of its
    fragments -- median rather than mean so a single outlier fragment
    cannot drag the fit. Rows must already be ordered top to bottom (as
    `cluster_fragments_into_rows` produces them); a global non-crossing
    constraint is asserted rather than silently repaired, since a crossing
    here means the input was not actually row-ordered."""
    baselines = []
    for row in rows:
        y = median(_fragment_center_y(f) for f in row)
        baselines.append(Curve(points=(Point(0.0, y), Point(page_width, y))))

    ys = [b.y_at(0.0) for b in baselines]
    if ys != sorted(ys):
        raise ValueError("row baselines are not monotone top to bottom")
    return baselines


def bands_from_baselines(
    baselines: Sequence[Curve], page_width: float, page_height: float
) -> list[RowBand]:
    """Expand each baseline to the midpoint of the gap to its neighbours --
    no rule is available to give extent directly. The first row's top and
    the last row's bottom extend to the page edges."""
    if not baselines:
        return []

    edges = [0.0]
    for a, b in pairwise(baselines):
        edges.append((a.y_at(0.0) + b.y_at(0.0)) / 2.0)
    edges.append(page_height)

    return [
        RowBand(
            top=Curve(points=(Point(0.0, top_y), Point(page_width, top_y))),
            bottom=Curve(points=(Point(0.0, bottom_y), Point(page_width, bottom_y))),
        )
        for top_y, bottom_y in pairwise(edges)
    ]
