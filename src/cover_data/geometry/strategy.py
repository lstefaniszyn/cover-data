"""Per-document row-extent strategy selection: ruled vs. borderless
(plan.md Phase 5, "Strategy selection").

Rule extraction runs first. If a coherent horizontal rule set spanning the
table is found, the ruled strategy owns the reported extents and the
borderless strategy still runs as an independent second opinion -- its
disagreement is a Phase 6 signal, not consumed here. If no rule set is
found, the borderless strategy owns the extents alone and `borderless` is
`True`: a property of the result, visible to the user, not a silent
internal branch.

The borderless path is computed from fragments alone in both modes and
never reads the ruled path's output, or the independence that makes
disagreement meaningful would be lost.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from cover_data.domain import OcrFragment
from cover_data.geometry.lines import LineSegment
from cover_data.geometry.rows_ruled import RowBand, build_ruled_row_bands
from cover_data.geometry.rows_text import (
    bands_from_baselines,
    cluster_fragments_into_rows,
    fit_row_baselines,
)


@dataclass(frozen=True)
class RowStrategyResult:
    bands: tuple[RowBand, ...]
    borderless: bool
    cross_check_bands: tuple[RowBand, ...] | None


def _borderless_bands(
    fragments: Sequence[OcrFragment], page_width: float, page_height: float
) -> tuple[RowBand, ...]:
    rows = cluster_fragments_into_rows(fragments)
    baselines = fit_row_baselines(rows, page_width=page_width) if rows else []
    return tuple(
        bands_from_baselines(baselines, page_width=page_width, page_height=page_height)
    )


def select_row_strategy(
    horizontal_lines: Sequence[LineSegment],
    fragments: Sequence[OcrFragment],
    page_width: float,
    page_height: float,
) -> RowStrategyResult:
    ruled_bands = tuple(
        build_ruled_row_bands(horizontal_lines, page_height=page_height)
    )
    if ruled_bands:
        cross_check = _borderless_bands(fragments, page_width, page_height)
        return RowStrategyResult(
            bands=ruled_bands, borderless=False, cross_check_bands=cross_check or None
        )

    text_bands = _borderless_bands(fragments, page_width, page_height)
    return RowStrategyResult(bands=text_bands, borderless=True, cross_check_bands=None)
