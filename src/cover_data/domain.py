"""Typed domain model for OCR fragments and the reconstructed table hierarchy.

Replaces raw dicts by design (see `CLAUDE.md` "Typing discipline"): the hard
problem in this project is keeping the OCR-fragment -> cell -> row -> person
relationship correct under skewed/wavy scans, and an untyped dict makes a
shape mismatch invisible until runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ColumnRole(StrEnum):
    """The searchable-field vocabulary (`CLAUDE.md` "Domain invariants"),
    plus `UNKNOWN` for a header that does not resolve. `UNKNOWN` is a first
    -class value, not an error -- a document whose header OCR fails still
    reconstructs rows, it just cannot be searched by that column."""

    LP = "lp"
    IMIE = "imie"
    NAZWISKO = "nazwisko"
    IMIE_I_NAZWISKO = "imie_i_nazwisko"
    PESEL = "pesel"
    ADRES = "adres"
    KWOTA = "kwota"
    WIERZYCIEL = "wierzyciel"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class BoundingBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float


@dataclass(frozen=True)
class OcrFragment:
    """One recognized text fragment, in original source-image pixels (never
    the OCR engine's internal preprocessed/unwarped space -- see
    `geometry.transform`).

    Confidence is retained on every fragment regardless of `low_confidence`:
    flagging never filters (FR-002), so a sub-threshold fragment still
    reaches the row model and the display.
    """

    text: str
    polygon: tuple[Point, Point, Point, Point]
    confidence: float
    low_confidence: bool

    @property
    def bbox(self) -> BoundingBox:
        """Derived from `polygon`, never stored, so it cannot desync from it."""
        xs = [p.x for p in self.polygon]
        ys = [p.y for p in self.polygon]
        return BoundingBox(min(xs), min(ys), max(xs), max(ys))


@dataclass(frozen=True)
class Cell:
    """A cell holds multiple fragments -- the two-line address is the normal
    case, not an edge case -- so `text` joins them in reading order rather
    than assuming one fragment per cell."""

    role: ColumnRole
    text: str
    fragments: tuple[OcrFragment, ...] = ()


@dataclass(frozen=True)
class TableRow:
    """A row's identity is `(table_index, position)`, both zero-based, both
    always present -- never derived from a recognized `Lp.` value, which is
    an ordinary `Cell` under `ColumnRole.LP` and nothing more. `Lp.` is
    absent entirely in layout C, `None`/blank on some rows, and
    non-monotonic on a continuation page -- deriving position from it would
    break all three (see plan.md Phase 4)."""

    table_index: int
    position: int
    cells: tuple[Cell, ...] = ()

    def cell(self, role: ColumnRole) -> Cell | None:
        for c in self.cells:
            if c.role is role:
                return c
        return None


@dataclass(frozen=True)
class Table:
    """A single-table page is the ordinary case, not a special one: it is a
    `Document` with one `Table`."""

    index: int
    columns: tuple[ColumnRole, ...]
    rows: tuple[TableRow, ...] = ()

    def __post_init__(self) -> None:
        for position, row in enumerate(self.rows):
            if row.table_index != self.index:
                raise ValueError(
                    f"row at position {position} carries table_index "
                    f"{row.table_index}, expected {self.index}"
                )
            if row.position != position:
                raise ValueError(
                    f"row {position} of table {self.index} carries "
                    f"position {row.position}, expected {position}"
                )

    def column_index(self, role: ColumnRole) -> int | None:
        """`None` is a correct answer, not an error -- e.g. layout B has no
        `IMIE` column, and asking for it should say so rather than raise."""
        try:
            return self.columns.index(role)
        except ValueError:
            return None

    def has_role(self, role: ColumnRole) -> bool:
        return role in self.columns


@dataclass(frozen=True)
class Document:
    """An ordered sequence of `Table`s. `23.png`'s two same-page tables are
    why this is a sequence rather than a single `Table`."""

    tables: tuple[Table, ...] = ()

    def __post_init__(self) -> None:
        for index, table in enumerate(self.tables):
            if table.index != index:
                raise ValueError(
                    f"table at position {index} carries index {table.index}"
                )
