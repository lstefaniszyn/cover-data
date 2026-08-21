"""Multi-table segmentation and cell assignment (plan.md Phase 5, "Multi
-table segmentation" and "Cell assignment and row assembly").

`23.png` carries two same-page tables separated by a vertical gap, each
with its own header row -- `segment_row_bands_by_gap` finds that gap, and
`is_header_like_row` recognizes the second header structurally (its cell
text matches its own column's role) rather than by position, since it
would otherwise look like an ordinary data row.

Cell assignment places each fragment into the cell whose row band and
column band contain it. A fragment outside every band (a margin signature
present on every generated fixture) is retained as unassigned, never
dropped -- it becomes a Phase 6 ambiguity signal. A blank cell is an empty
`Cell`, never a missing one (`21.png`'s blank row must not collapse the
row index).
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise
from statistics import median

from cover_data.domain import Cell, ColumnRole, OcrFragment, Table, TableRow
from cover_data.geometry.columns import ColumnBand, resolve_column_role
from cover_data.geometry.rows_ruled import RowBand


def _fragment_center(fragment: OcrFragment) -> tuple[float, float]:
    bbox = fragment.bbox
    return (bbox.x_min + bbox.x_max) / 2.0, (bbox.y_min + bbox.y_max) / 2.0


def _row_index_for(row_bands: Sequence[RowBand], x: float, y: float) -> int | None:
    for index, band in enumerate(row_bands):
        if band.top.y_at(x) <= y < band.bottom.y_at(x):
            return index
    return None


def _column_index_for(column_bands: Sequence[ColumnBand], x: float) -> int | None:
    for index, band in enumerate(column_bands):
        if band.left <= x < band.right:
            return index
    return None


def build_table(
    row_bands: Sequence[RowBand],
    column_bands: Sequence[ColumnBand],
    fragments: Sequence[OcrFragment],
    table_index: int,
) -> tuple[Table, tuple[OcrFragment, ...]]:
    """Assigns each fragment to the cell whose row band and column band
    contain it, then assembles the `Table`. Returns the table and every
    fragment that fell outside every band, in original order."""
    buckets: dict[tuple[int, int], list[OcrFragment]] = {}
    unassigned: list[OcrFragment] = []

    for fragment in fragments:
        x, y = _fragment_center(fragment)
        row_index = _row_index_for(row_bands, x, y)
        column_index = _column_index_for(column_bands, x)
        if row_index is None or column_index is None:
            unassigned.append(fragment)
            continue
        buckets.setdefault((row_index, column_index), []).append(fragment)

    rows = []
    for row_index in range(len(row_bands)):
        cells = []
        for column_index, column_band in enumerate(column_bands):
            cell_fragments = tuple(
                sorted(
                    buckets.get((row_index, column_index), []),
                    key=lambda f: (_fragment_center(f)[1], _fragment_center(f)[0]),
                )
            )
            text = " ".join(f.text for f in cell_fragments)
            cells.append(
                Cell(role=column_band.role, text=text, fragments=cell_fragments)
            )
        rows.append(
            TableRow(table_index=table_index, position=row_index, cells=tuple(cells))
        )

    table = Table(
        index=table_index,
        columns=tuple(cb.role for cb in column_bands),
        rows=tuple(rows),
    )
    return table, tuple(unassigned)


def segment_row_bands_by_gap(
    row_bands: Sequence[RowBand], gap_frac: float = 2.0
) -> list[list[RowBand]]:
    """Split row bands into table groups wherever the vertical gap between
    consecutive bands exceeds `gap_frac` times the median row height --
    `23.png`'s two same-page tables are separated by exactly such a gap."""
    if not row_bands:
        return []
    if len(row_bands) == 1:
        return [[row_bands[0]]]

    heights = [b.bottom.y_at(0.0) - b.top.y_at(0.0) for b in row_bands]
    threshold = gap_frac * median(heights)

    groups: list[list[RowBand]] = [[row_bands[0]]]
    for prev, current in pairwise(row_bands):
        gap = current.top.y_at(0.0) - prev.bottom.y_at(0.0)
        if gap > threshold:
            groups.append([])
        groups[-1].append(current)
    return groups


def is_header_like_row(row: TableRow, columns: Sequence[ColumnRole]) -> bool:
    """A row counts as a repeated header when at least half of its
    non-empty cells resolve, by their own text, to the role their column
    already carries -- structural recognition, not a positional guess."""
    if not row.cells:
        return False
    matches = sum(
        1
        for cell, role in zip(row.cells, columns, strict=True)
        if cell.text
        and resolve_column_role(cell.text) is role
        and role is not ColumnRole.UNKNOWN
    )
    return matches >= max(1, len(columns) // 2)
