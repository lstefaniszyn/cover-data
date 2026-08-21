from __future__ import annotations

from cover_data.domain import ColumnRole, OcrFragment, Point
from cover_data.geometry.document import reconstruct_document
from cover_data.geometry.lines import LineSegment

PAGE_WIDTH = 200.0
PAGE_HEIGHT = 150.0


def _frag(text: str, x0: float, y0: float, x1: float, y1: float) -> OcrFragment:
    return OcrFragment(
        text=text,
        polygon=(Point(x0, y0), Point(x1, y0), Point(x1, y1), Point(x0, y1)),
        confidence=0.99,
        low_confidence=False,
    )


def _hrule(y: float) -> LineSegment:
    return LineSegment(x0=0.0, y0=y, x1=PAGE_WIDTH, y1=y)


def _vrule(x: float, y0: float, y1: float) -> LineSegment:
    return LineSegment(x0=x, y0=y0, x1=x, y1=y1)


def test_reconstructs_a_single_ruled_table_with_header_and_one_data_row() -> None:
    horizontal_lines = [_hrule(10.0), _hrule(40.0), _hrule(70.0)]
    vertical_lines = [
        _vrule(0.0, 10.0, 70.0),
        _vrule(100.0, 10.0, 70.0),
        _vrule(200.0, 10.0, 70.0),
    ]
    fragments = [
        _frag("Imię", 10, 15, 90, 35),
        _frag("Nazwisko", 110, 15, 190, 35),
        _frag("Anna", 10, 45, 90, 65),
        _frag("Nowak", 110, 45, 190, 65),
    ]

    document, unassigned, borderless = reconstruct_document(
        fragments, horizontal_lines, vertical_lines, PAGE_WIDTH, PAGE_HEIGHT
    )

    assert borderless is False
    assert unassigned == ()
    (table,) = document.tables
    assert table.columns == (ColumnRole.IMIE, ColumnRole.NAZWISKO)
    (row,) = table.rows
    assert row.cell(ColumnRole.IMIE).text == "Anna"
    assert row.cell(ColumnRole.NAZWISKO).text == "Nowak"


def test_falls_back_to_borderless_when_there_are_no_rules() -> None:
    fragments = [
        _frag("Imię", 10, 10, 90, 30),
        _frag("Nazwisko", 110, 11, 190, 31),
        _frag("Anna", 10, 60, 90, 80),
        _frag("Nowak", 110, 61, 190, 81),
    ]

    document, _unassigned, borderless = reconstruct_document(
        fragments, [], [], PAGE_WIDTH, PAGE_HEIGHT
    )

    assert borderless is True
    (table,) = document.tables
    assert len(table.rows) == 1


def test_header_only_page_yields_a_table_with_zero_rows() -> None:
    horizontal_lines = [_hrule(10.0), _hrule(40.0)]
    vertical_lines = [
        _vrule(0.0, 10.0, 40.0),
        _vrule(100.0, 10.0, 40.0),
        _vrule(200.0, 10.0, 40.0),
    ]
    fragments = [_frag("Imię", 10, 15, 90, 35), _frag("Nazwisko", 110, 15, 190, 35)]

    document, _unassigned, _borderless = reconstruct_document(
        fragments, horizontal_lines, vertical_lines, PAGE_WIDTH, PAGE_HEIGHT
    )

    (table,) = document.tables
    assert table.rows == ()


def test_two_tables_separated_by_a_gap_yield_two_distinguishable_tables() -> None:
    horizontal_lines = [
        _hrule(10.0),
        _hrule(40.0),
        _hrule(70.0),
        _hrule(400.0),
        _hrule(430.0),
        _hrule(460.0),
    ]
    vertical_lines = [
        _vrule(0.0, 10.0, 70.0),
        _vrule(200.0, 10.0, 70.0),
        _vrule(0.0, 400.0, 460.0),
        _vrule(200.0, 400.0, 460.0),
    ]
    fragments = [
        _frag("Imię", 10, 15, 190, 35),
        _frag("Anna", 10, 45, 190, 65),
        _frag("Imię", 10, 405, 190, 425),
        _frag("Ola", 10, 435, 190, 455),
    ]

    document, _unassigned, _borderless = reconstruct_document(
        fragments,
        horizontal_lines,
        vertical_lines,
        PAGE_WIDTH,
        page_height=500.0,
    )

    assert len(document.tables) == 2
    assert document.tables[0].index == 0
    assert document.tables[1].index == 1
    row_a = document.tables[0].rows[0]
    row_b = document.tables[1].rows[0]
    assert row_a.table_index == 0
    assert row_b.table_index == 1
