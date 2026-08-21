"""Ruled row strategy: turn consecutive horizontal rules into row extents
(plan.md Phase 5, "Ruled row strategy").

A `RowBand`'s top and bottom are each a `Curve` sampled across the page
width, never a scalar y -- `11.png`'s 19px wave means no single y-value can
bound the row correctly at both ends of the page (plan.md "Row extent
under waviness is a polyline, not a scalar").
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from cover_data.domain import Point
from cover_data.geometry.lines import LineSegment


@dataclass(frozen=True)
class Curve:
    """A boundary sampled as a polyline across the page width, ordered by
    x. A straight rule degenerates to two points; a future wavy-rule
    detector can supply more without changing this contract."""

    points: tuple[Point, ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("a curve needs at least two points")
        xs = [p.x for p in self.points]
        if xs != sorted(xs):
            raise ValueError("curve points must be ordered by x")

    def y_at(self, x: float) -> float:
        """Linear interpolation between the two bracketing samples; clamps
        to the nearest endpoint outside the sampled span rather than
        extrapolating."""
        pts = self.points
        if x <= pts[0].x:
            return pts[0].y
        if x >= pts[-1].x:
            return pts[-1].y
        for a, b in pairwise(pts):
            if a.x <= x <= b.x:
                if b.x == a.x:
                    return a.y
                t = (x - a.x) / (b.x - a.x)
                return a.y + t * (b.y - a.y)
        return pts[-1].y


@dataclass(frozen=True)
class RowBand:
    top: Curve
    bottom: Curve


def _line_to_curve(line: LineSegment) -> Curve:
    return Curve(points=(Point(line.x0, line.y0), Point(line.x1, line.y1)))


def build_ruled_row_bands(
    horizontal_lines: Sequence[LineSegment],
    page_height: float,
    min_band_height_frac: float = 0.01,
) -> list[RowBand]:
    """Consecutive rule pairs become row bands, ordered top to bottom.
    A band thinner than `min_band_height_frac` of `page_height` is an
    artifact (a near-duplicate detected rule) and is discarded."""
    if len(horizontal_lines) < 2:
        return []

    ordered = sorted(horizontal_lines, key=lambda ln: (ln.y0 + ln.y1) / 2.0)
    min_height = min_band_height_frac * page_height

    bands = []
    for top_line, bottom_line in pairwise(ordered):
        top_y = (top_line.y0 + top_line.y1) / 2.0
        bottom_y = (bottom_line.y0 + bottom_line.y1) / 2.0
        if bottom_y - top_y < min_height:
            continue
        bands.append(
            RowBand(top=_line_to_curve(top_line), bottom=_line_to_curve(bottom_line))
        )
    return bands


def extend_band_bottom_to_edge(band: RowBand, edge_y: float) -> RowBand:
    """Replace `band.bottom` with a flat line at `edge_y`, spanning the
    same x-range -- for a row with no closing rule before the page edge
    (`18.png`'s bottom-truncated row 23). The band must extend to the page
    edge, never to detected content extent (plan.md Phase 5, Risk #1)."""
    x0 = band.bottom.points[0].x
    x1 = band.bottom.points[-1].x
    return RowBand(
        top=band.top, bottom=Curve(points=(Point(x0, edge_y), Point(x1, edge_y)))
    )
