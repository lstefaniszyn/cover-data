from __future__ import annotations

import pytest

from cover_data.domain import OcrFragment, Point
from cover_data.geometry.rows_text import (
    bands_from_baselines,
    cluster_fragments_into_rows,
    fit_row_baselines,
)


def _frag(x0: float, y0: float, x1: float, y1: float, text: str = "x") -> OcrFragment:
    return OcrFragment(
        text=text,
        polygon=(Point(x0, y0), Point(x1, y0), Point(x1, y1), Point(x0, y1)),
        confidence=0.99,
        low_confidence=False,
    )


def test_clusters_fragments_into_rows_by_vertical_gap() -> None:
    # Two rows, each ~20px tall, separated by a clear gap.
    row1 = [_frag(10, 10, 60, 30), _frag(70, 11, 150, 31)]
    row2 = [_frag(10, 60, 60, 80), _frag(70, 61, 150, 81)]

    rows = cluster_fragments_into_rows([*row1, *row2])

    assert len(rows) == 2
    assert {f.text for f in rows[0]} == {"x"}
    assert len(rows[0]) == 2
    assert len(rows[1]) == 2


def test_a_stray_fragment_inside_a_rows_vertical_span_does_not_split_it() -> None:
    row = [
        _frag(10, 10, 60, 30, text="a"),
        _frag(70, 12, 150, 32, text="b"),
        _frag(200, 18, 210, 24, text="stray"),  # small, off-center but still in-span
    ]

    rows = cluster_fragments_into_rows(row)

    assert len(rows) == 1
    assert len(rows[0]) == 3


def test_fit_row_baselines_uses_the_median_so_one_outlier_does_not_drag_it() -> None:
    row = [
        _frag(0, 10, 20, 30),
        _frag(30, 10, 50, 30),
        _frag(60, 40, 80, 60),
    ]  # outlier

    (baseline,) = fit_row_baselines([row], page_width=200.0)

    # Median center of {20, 20, 50} is 20 -- the outlier does not move it.
    assert baseline.y_at(0.0) == pytest.approx(20.0)


def test_fit_row_baselines_rejects_non_monotone_input() -> None:
    row_low = [_frag(0, 100, 20, 120)]
    row_high = [_frag(0, 10, 20, 30)]

    with pytest.raises(ValueError, match="monotone"):
        fit_row_baselines([row_low, row_high], page_width=200.0)


def test_bands_from_baselines_expand_to_midpoints_and_page_edges() -> None:
    baselines = fit_row_baselines(
        [[_frag(0, 10, 20, 30)], [_frag(0, 90, 20, 110)]], page_width=200.0
    )

    bands = bands_from_baselines(baselines, page_width=200.0, page_height=150.0)

    assert len(bands) == 2
    assert bands[0].top.y_at(0.0) == pytest.approx(0.0)
    assert bands[0].bottom.y_at(0.0) == pytest.approx(60.0)  # midpoint of 20 and 100
    assert bands[1].top.y_at(0.0) == pytest.approx(60.0)
    assert bands[1].bottom.y_at(0.0) == pytest.approx(150.0)
