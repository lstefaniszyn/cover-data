"""Column schema and role resolution (plan.md Phase 5, "Column schema and
role resolution") -- the enabling contract for S-02's `--field`.

Column position differs across layouts A, B and C -- `Imię` is column 2 in
A and absent in B, where it is merged into `Imię i nazwisko` -- so a role
is a named property of a column, not an index a consumer is expected to
know. Role resolution is tolerant of OCR noise (a dropped diacritic, mixed
case) and of the multi-line header `Kwota / zadłużenia / (PLN)`; an
unmatched header resolves to `unknown` rather than to a guess.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from cover_data.domain import ColumnRole, OcrFragment
from cover_data.geometry.lines import LineSegment


@dataclass(frozen=True)
class ColumnBand:
    left: float
    right: float
    header_text: str
    role: ColumnRole


def _normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def resolve_column_role(header_text: str) -> ColumnRole:
    """Matches recognized header text against the known Polish header
    vocabulary (`CLAUDE.md` "Domain invariants"). Checked before the split
    -name roles, since "imię" is a substring of "imię i nazwisko"."""
    normalized = _normalize(header_text)
    if "imię i nazwisko" in normalized or "imie i nazwisko" in normalized:
        return ColumnRole.IMIE_I_NAZWISKO
    if normalized.startswith("lp"):
        return ColumnRole.LP
    if "nazwisko" in normalized:
        return ColumnRole.NAZWISKO
    if "imię" in normalized or "imie" in normalized:
        return ColumnRole.IMIE
    if "pesel" in normalized:
        return ColumnRole.PESEL
    if "adres" in normalized:
        return ColumnRole.ADRES
    if "kwota" in normalized:
        return ColumnRole.KWOTA
    if "wierzyciel" in normalized:
        return ColumnRole.WIERZYCIEL
    return ColumnRole.UNKNOWN


def _header_text_in_band(
    fragments: Sequence[OcrFragment], left: float, right: float
) -> str:
    in_band = [
        f for f in fragments if left <= (f.bbox.x_min + f.bbox.x_max) / 2.0 < right
    ]
    in_band.sort(key=lambda f: (f.bbox.y_min, f.bbox.x_min))
    return " ".join(f.text for f in in_band)


def build_column_bands(
    vertical_lines: Sequence[LineSegment],
    header_fragments: Sequence[OcrFragment],
    page_width: float,
) -> list[ColumnBand]:
    """Consecutive vertical rule pairs become column bands, ordered left to
    right, each carrying the header text recognized within it and the
    role that text resolves to."""
    if len(vertical_lines) < 2:
        return []

    xs = sorted((line.x0 + line.x1) / 2.0 for line in vertical_lines)
    bands = []
    for left, right in pairwise(xs):
        text = _header_text_in_band(header_fragments, left, right)
        bands.append(
            ColumnBand(
                left=left, right=right, header_text=text, role=resolve_column_role(text)
            )
        )
    return bands


def extend_last_column_to_edge(
    bands: Sequence[ColumnBand], edge_x: float
) -> list[ColumnBand]:
    """Replace the last band's right bound with `edge_x` -- for a column
    with no closing rule before the page edge (`5.png`'s rightmost column).
    The band must extend to the page edge, never to detected content
    extent (plan.md Phase 5, Risk #1)."""
    if not bands:
        return []
    *rest, last = bands
    extended = ColumnBand(
        left=last.left, right=edge_x, header_text=last.header_text, role=last.role
    )
    return [*rest, extended]
