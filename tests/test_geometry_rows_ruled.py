from __future__ import annotations

from cover_data.domain import Point
from cover_data.geometry.lines import LineSegment
from cover_data.geometry.rows_ruled import (
    Curve,
    build_ruled_row_bands,
    extend_band_bottom_to_edge,
)


def _rule(y: float, x0: float = 0.0, x1: float = 200.0) -> LineSegment:
    return LineSegment(x0=x0, y0=y, x1=x1, y1=y)


def test_pairs_consecutive_rules_into_bands_top_to_bottom() -> None:
    rules = [_rule(110.0), _rule(10.0), _rule(60.0)]  # deliberately out of order

    bands = build_ruled_row_bands(rules, page_height=150.0)

    assert len(bands) == 2
    assert bands[0].top.y_at(0.0) == 10.0
    assert bands[0].bottom.y_at(0.0) == 60.0
    assert bands[1].top.y_at(0.0) == 60.0
    assert bands[1].bottom.y_at(0.0) == 110.0


def test_discards_a_band_thinner_than_the_page_relative_minimum() -> None:
    # 10 and 12 are 2px apart on a 150px-tall page (~1.3%), well under the
    # default 5% minimum -- an artifact, not a real row.
    rules = [_rule(10.0), _rule(12.0), _rule(90.0)]

    bands = build_ruled_row_bands(rules, page_height=150.0, min_band_height_frac=0.05)

    assert len(bands) == 1
    assert bands[0].top.y_at(0.0) == 12.0
    assert bands[0].bottom.y_at(0.0) == 90.0


def test_fewer_than_two_rules_yields_no_bands() -> None:
    assert build_ruled_row_bands([_rule(10.0)], page_height=150.0) == []
    assert build_ruled_row_bands([], page_height=150.0) == []


def test_curve_interpolates_linearly_between_sample_points() -> None:
    curve = Curve(points=(Point(0.0, 10.0), Point(100.0, 30.0)))

    assert curve.y_at(0.0) == 10.0
    assert curve.y_at(100.0) == 30.0
    assert curve.y_at(50.0) == 20.0
    # Outside the sampled span, the boundary value clamps rather than
    # extrapolating.
    assert curve.y_at(-10.0) == 10.0
    assert curve.y_at(200.0) == 30.0


def test_extend_band_bottom_to_edge_replaces_bottom_with_a_flat_line() -> None:
    rules = [_rule(10.0), _rule(60.0)]
    (band,) = build_ruled_row_bands(rules, page_height=150.0)

    extended = extend_band_bottom_to_edge(band, edge_y=150.0)

    assert extended.top.y_at(0.0) == 10.0
    assert extended.bottom.y_at(0.0) == 150.0
    assert extended.bottom.y_at(200.0) == 150.0
