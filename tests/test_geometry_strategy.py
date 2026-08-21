from __future__ import annotations

from cover_data.domain import OcrFragment, Point
from cover_data.geometry.lines import LineSegment
from cover_data.geometry.rows_text import (
    bands_from_baselines,
    cluster_fragments_into_rows,
    fit_row_baselines,
)
from cover_data.geometry.strategy import select_row_strategy

PAGE_WIDTH = 200.0
PAGE_HEIGHT = 150.0


def _rule(y: float) -> LineSegment:
    return LineSegment(x0=0.0, y0=y, x1=PAGE_WIDTH, y1=y)


def _frag(x0: float, y0: float, x1: float, y1: float) -> OcrFragment:
    return OcrFragment(
        text="x",
        polygon=(Point(x0, y0), Point(x1, y0), Point(x1, y1), Point(x0, y1)),
        confidence=0.99,
        low_confidence=False,
    )


def test_selects_ruled_strategy_and_keeps_borderless_as_a_second_opinion() -> None:
    rules = [_rule(10.0), _rule(60.0), _rule(110.0)]
    fragments = [_frag(10, 15, 60, 35), _frag(10, 65, 60, 85)]

    result = select_row_strategy(
        horizontal_lines=rules,
        fragments=fragments,
        page_width=PAGE_WIDTH,
        page_height=PAGE_HEIGHT,
    )

    assert result.borderless is False
    assert len(result.bands) == 2
    assert result.bands[0].top.y_at(0.0) == 10.0
    assert result.cross_check_bands is not None
    assert len(result.cross_check_bands) == 2


def test_falls_back_to_borderless_when_no_coherent_rule_set_exists() -> None:
    fragments = [
        _frag(10, 10, 60, 30),
        _frag(70, 11, 150, 31),
        _frag(10, 60, 60, 80),
        _frag(70, 61, 150, 81),
    ]

    result = select_row_strategy(
        horizontal_lines=[],
        fragments=fragments,
        page_width=PAGE_WIDTH,
        page_height=PAGE_HEIGHT,
    )

    assert result.borderless is True
    assert len(result.bands) == 2
    assert result.cross_check_bands is None


def test_borderless_cross_check_is_independent_of_the_ruled_bands() -> None:
    rules = [_rule(10.0), _rule(60.0), _rule(110.0)]
    fragments = [_frag(10, 15, 60, 35), _frag(10, 65, 60, 85)]

    result = select_row_strategy(
        horizontal_lines=rules,
        fragments=fragments,
        page_width=PAGE_WIDTH,
        page_height=PAGE_HEIGHT,
    )

    standalone_rows = cluster_fragments_into_rows(fragments)
    standalone_baselines = fit_row_baselines(standalone_rows, page_width=PAGE_WIDTH)
    standalone_bands = bands_from_baselines(
        standalone_baselines, page_width=PAGE_WIDTH, page_height=PAGE_HEIGHT
    )

    assert result.cross_check_bands is not None
    for got, expected in zip(result.cross_check_bands, standalone_bands, strict=True):
        assert got.top.y_at(0.0) == expected.top.y_at(0.0)
        assert got.bottom.y_at(0.0) == expected.bottom.y_at(0.0)
