from __future__ import annotations

import pytest

from cover_data.domain import Point
from cover_data.geometry.transform import OrientationTransform


@pytest.mark.parametrize("angle", [0, 90, 180, 270])
def test_orientation_transform_round_trips_for_every_angle(angle: int) -> None:
    """A known point mapped through the orientation transform and back lands
    within tolerance of itself -- the round-trip the coordinate contract
    depends on (plan.md Phase 4)."""
    transform = OrientationTransform(angle=angle, source_width=1240, source_height=864)
    point = Point(317.5, 604.2)

    forward = transform.forward(point)
    back = transform.inverse(forward)

    assert back.x == pytest.approx(point.x, abs=1e-6)
    assert back.y == pytest.approx(point.y, abs=1e-6)


@pytest.mark.parametrize("angle", [90, 270])
def test_orientation_transform_swaps_dimensions_for_quarter_turns(angle: int) -> None:
    transform = OrientationTransform(angle=angle, source_width=1240, source_height=864)

    assert transform.rotated_width == 864
    assert transform.rotated_height == 1240


def test_orientation_transform_is_identity_at_zero_degrees() -> None:
    transform = OrientationTransform(angle=0, source_width=1240, source_height=864)
    point = Point(11.0, 22.0)

    assert transform.forward(point) == point
    assert transform.inverse(point) == point


def test_orientation_transform_rejects_an_unsupported_angle() -> None:
    with pytest.raises(ValueError, match="angle"):
        OrientationTransform(angle=45, source_width=100, source_height=100)
