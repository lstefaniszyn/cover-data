from __future__ import annotations

import pytest

from cover_data.domain import Cell, ColumnRole, Document, Table, TableRow


def test_row_identity_distinguishes_two_tables_sharing_position_zero() -> None:
    """23.png puts two tables on one page, both numbered from 1 -- a flat
    row list makes "row 1" ambiguous. Identity must be (table_index,
    position), not position alone."""
    doc = Document(
        tables=(
            Table(index=0, columns=(ColumnRole.NAZWISKO,), rows=(TableRow(0, 0),)),
            Table(index=1, columns=(ColumnRole.NAZWISKO,), rows=(TableRow(1, 0),)),
        )
    )
    row_a = doc.tables[0].rows[0]
    row_b = doc.tables[1].rows[0]
    assert row_a.position == row_b.position == 0
    assert row_a.table_index != row_b.table_index
    assert (row_a.table_index, row_a.position) != (row_b.table_index, row_b.position)


@pytest.mark.parametrize(
    "lp_value",
    [None, "", "7"],  # absent, blank, and non-monotonic (26.png: rows read 6,7,8)
    ids=["absent", "empty", "non_monotonic"],
)
def test_row_position_holds_regardless_of_lp_cell_value(lp_value: str | None) -> None:
    """21.png's blank row and 26.png's non-monotonic continuation page are
    why position must never be derived from the recognized `Lp.` value."""
    lp_cell = Cell(role=ColumnRole.LP, text=lp_value or "")
    row = TableRow(table_index=0, position=2, cells=(lp_cell,))
    assert row.position == 2
    assert row.cell(ColumnRole.LP) is lp_cell


def test_table_role_lookup_differs_between_layout_a_and_layout_b() -> None:
    layout_a = Table(
        index=0,
        columns=(
            ColumnRole.LP,
            ColumnRole.IMIE,
            ColumnRole.NAZWISKO,
            ColumnRole.PESEL,
        ),
    )
    layout_b = Table(
        index=0,
        columns=(ColumnRole.LP, ColumnRole.IMIE_I_NAZWISKO, ColumnRole.PESEL),
    )

    assert layout_a.column_index(ColumnRole.IMIE) == 1
    assert layout_a.column_index(ColumnRole.IMIE_I_NAZWISKO) is None

    assert layout_b.column_index(ColumnRole.IMIE) is None
    assert layout_b.column_index(ColumnRole.IMIE_I_NAZWISKO) == 1


def test_table_rejects_a_row_carrying_the_wrong_table_index() -> None:
    """Row identity is load-bearing enough to fail fast on construction
    rather than silently misreport a row's table."""
    with pytest.raises(ValueError, match="table_index"):
        Table(index=0, columns=(ColumnRole.LP,), rows=(TableRow(1, 0),))


def test_table_rejects_a_row_at_the_wrong_position() -> None:
    with pytest.raises(ValueError, match="position"):
        Table(index=0, columns=(ColumnRole.LP,), rows=(TableRow(0, 1),))
