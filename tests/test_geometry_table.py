from __future__ import annotations

from cover_data.domain import ColumnRole, OcrFragment, Point
from cover_data.geometry.columns import ColumnBand
from cover_data.geometry.rows_ruled import Curve, RowBand
from cover_data.geometry.table import (
    build_table,
    is_header_like_row,
    segment_row_bands_by_gap,
)


def _frag(text: str, x0: float, y0: float, x1: float, y1: float) -> OcrFragment:
    return OcrFragment(
        text=text,
        polygon=(Point(x0, y0), Point(x1, y0), Point(x1, y1), Point(x0, y1)),
        confidence=0.99,
        low_confidence=False,
    )


def _flat_row_band(top: float, bottom: float, width: float = 200.0) -> RowBand:
    return RowBand(
        top=Curve(points=(Point(0.0, top), Point(width, top))),
        bottom=Curve(points=(Point(0.0, bottom), Point(width, bottom))),
    )


def test_assigns_fragments_to_the_cell_whose_row_and_column_contain_them() -> None:
    row_bands = [_flat_row_band(0.0, 30.0)]
    column_bands = [
        ColumnBand(left=0.0, right=100.0, header_text="Imię", role=ColumnRole.IMIE),
        ColumnBand(
            left=100.0, right=200.0, header_text="Nazwisko", role=ColumnRole.NAZWISKO
        ),
    ]
    fragments = [_frag("Anna", 10, 5, 60, 25), _frag("Nowak", 110, 5, 160, 25)]

    table, unassigned = build_table(row_bands, column_bands, fragments, table_index=0)

    assert unassigned == ()
    (row,) = table.rows
    assert row.cell(ColumnRole.IMIE).text == "Anna"
    assert row.cell(ColumnRole.NAZWISKO).text == "Nowak"


def test_blank_cell_is_empty_not_missing() -> None:
    row_bands = [_flat_row_band(0.0, 30.0)]
    column_bands = [
        ColumnBand(left=0.0, right=100.0, header_text="Imię", role=ColumnRole.IMIE),
        ColumnBand(
            left=100.0, right=200.0, header_text="Nazwisko", role=ColumnRole.NAZWISKO
        ),
    ]
    fragments = [_frag("Anna", 10, 5, 60, 25)]  # no fragment in the Nazwisko column

    table, _unassigned = build_table(row_bands, column_bands, fragments, table_index=0)

    (row,) = table.rows
    assert len(row.cells) == 2
    blank = row.cell(ColumnRole.NAZWISKO)
    assert blank is not None
    assert blank.text == ""
    assert blank.fragments == ()


def test_fragment_outside_every_band_is_retained_as_unassigned() -> None:
    row_bands = [_flat_row_band(0.0, 30.0)]
    column_bands = [
        ColumnBand(left=0.0, right=100.0, header_text="Imię", role=ColumnRole.IMIE)
    ]
    stray = _frag("podpis", 10, 500, 60, 520)  # a margin signature far below the table
    fragments = [_frag("Anna", 10, 5, 60, 25), stray]

    table, unassigned = build_table(row_bands, column_bands, fragments, table_index=0)

    assert unassigned == (stray,)
    (row,) = table.rows
    assert "podpis" not in row.cell(ColumnRole.IMIE).text


def test_multiple_fragments_in_one_cell_join_top_to_bottom() -> None:
    row_bands = [_flat_row_band(0.0, 50.0)]
    column_bands = [
        ColumnBand(left=0.0, right=200.0, header_text="Adres", role=ColumnRole.ADRES)
    ]
    fragments = [
        _frag("ul. Polna 2", 10, 25, 100, 40),
        _frag("00-001 Warszawa", 10, 5, 100, 20),
    ]

    table, _unassigned = build_table(row_bands, column_bands, fragments, table_index=0)

    (row,) = table.rows
    assert row.cell(ColumnRole.ADRES).text == "00-001 Warszawa ul. Polna 2"


def test_segments_row_bands_by_a_large_vertical_gap() -> None:
    bands = [
        _flat_row_band(0.0, 30.0),
        _flat_row_band(30.0, 60.0),
        _flat_row_band(400.0, 430.0),  # a big gap before this one
        _flat_row_band(430.0, 460.0),
    ]

    groups = segment_row_bands_by_gap(bands, gap_frac=2.0)

    assert len(groups) == 2
    assert len(groups[0]) == 2
    assert len(groups[1]) == 2


def test_no_gap_yields_a_single_group() -> None:
    bands = [
        _flat_row_band(0.0, 30.0),
        _flat_row_band(30.0, 60.0),
        _flat_row_band(60.0, 90.0),
    ]

    groups = segment_row_bands_by_gap(bands, gap_frac=2.0)

    assert len(groups) == 1
    assert len(groups[0]) == 3


def test_is_header_like_row_true_when_cell_text_matches_its_own_role() -> None:
    row_bands = [_flat_row_band(0.0, 30.0)]
    column_bands = [
        ColumnBand(left=0.0, right=100.0, header_text="Imię", role=ColumnRole.IMIE),
        ColumnBand(
            left=100.0, right=200.0, header_text="Nazwisko", role=ColumnRole.NAZWISKO
        ),
    ]
    fragments = [_frag("Imię", 10, 5, 60, 25), _frag("Nazwisko", 110, 5, 160, 25)]
    table, _unassigned = build_table(row_bands, column_bands, fragments, table_index=0)

    assert is_header_like_row(table.rows[0], table.columns) is True


def test_is_header_like_row_false_for_ordinary_data() -> None:
    row_bands = [_flat_row_band(0.0, 30.0)]
    column_bands = [
        ColumnBand(left=0.0, right=100.0, header_text="Imię", role=ColumnRole.IMIE),
        ColumnBand(
            left=100.0, right=200.0, header_text="Nazwisko", role=ColumnRole.NAZWISKO
        ),
    ]
    fragments = [_frag("Anna", 10, 5, 60, 25), _frag("Nowak", 110, 5, 160, 25)]
    table, _unassigned = build_table(row_bands, column_bands, fragments, table_index=0)

    assert is_header_like_row(table.rows[0], table.columns) is False
