from __future__ import annotations

import pytest

from cover_data.domain import ColumnRole, OcrFragment, Point
from cover_data.geometry.columns import (
    build_column_bands,
    extend_last_column_to_edge,
    resolve_column_role,
)
from cover_data.geometry.lines import LineSegment


def _frag(text: str, x0: float, y0: float, x1: float, y1: float) -> OcrFragment:
    return OcrFragment(
        text=text,
        polygon=(Point(x0, y0), Point(x1, y0), Point(x1, y1), Point(x0, y1)),
        confidence=0.99,
        low_confidence=False,
    )


@pytest.mark.parametrize(
    ("header_text", "expected"),
    [
        ("Lp.", ColumnRole.LP),
        ("Imię", ColumnRole.IMIE),
        ("Nazwisko", ColumnRole.NAZWISKO),
        ("Imię i nazwisko", ColumnRole.IMIE_I_NAZWISKO),
        ("PESEL", ColumnRole.PESEL),
        ("Adres zamieszkania", ColumnRole.ADRES),
        ("Adres", ColumnRole.ADRES),
        ("Kwota zadłużenia (PLN)", ColumnRole.KWOTA),
        (
            "Kwota zadłużenia ( PLN )",
            ColumnRole.KWOTA,
        ),  # multi-line header joined with spaces
        ("Wierzyciel", ColumnRole.WIERZYCIEL),
        ("imie", ColumnRole.IMIE),  # OCR noise: diacritic dropped
        ("???", ColumnRole.UNKNOWN),
        ("", ColumnRole.UNKNOWN),
    ],
)
def test_resolve_column_role(header_text: str, expected: ColumnRole) -> None:
    assert resolve_column_role(header_text) is expected


def test_build_column_bands_resolves_a_split_name_layout() -> None:
    verticals = [
        LineSegment(x0=0.0, y0=0.0, x1=0.0, y1=100.0),
        LineSegment(x0=50.0, y0=0.0, x1=50.0, y1=100.0),
        LineSegment(x0=150.0, y0=0.0, x1=150.0, y1=100.0),
    ]
    headers = [
        _frag("Imię", 5.0, 5.0, 45.0, 20.0),
        _frag("Nazwisko", 55.0, 5.0, 145.0, 20.0),
    ]

    bands = build_column_bands(verticals, headers, page_width=200.0)

    assert len(bands) == 2
    assert bands[0].role is ColumnRole.IMIE
    assert bands[1].role is ColumnRole.NAZWISKO


def test_build_column_bands_joins_a_two_line_header_top_to_bottom() -> None:
    verticals = [
        LineSegment(x0=0.0, y0=0.0, x1=0.0, y1=100.0),
        LineSegment(x0=100.0, y0=0.0, x1=100.0, y1=100.0),
    ]
    headers = [
        _frag("Kwota", 10.0, 5.0, 90.0, 15.0),
        _frag("zadłużenia (PLN)", 10.0, 18.0, 90.0, 28.0),
    ]

    (band,) = build_column_bands(verticals, headers, page_width=200.0)

    assert band.role is ColumnRole.KWOTA
    assert "Kwota" in band.header_text


def test_extend_last_column_to_edge_only_touches_the_final_band() -> None:
    verticals = [
        LineSegment(x0=0.0, y0=0.0, x1=0.0, y1=100.0),
        LineSegment(x0=50.0, y0=0.0, x1=50.0, y1=100.0),
    ]
    headers = [_frag("Imię", 5.0, 5.0, 45.0, 20.0)]
    bands = build_column_bands(verticals, headers, page_width=200.0)

    extended = extend_last_column_to_edge(bands, edge_x=200.0)

    assert extended[-1].right == 200.0
    assert extended[-1].role is bands[-1].role
    assert extended[:-1] == bands[:-1]
