from __future__ import annotations

from cover_data.domain import OcrFragment, Point
from cover_data.ocr.engine import flag_low_confidence

_POLY = (Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10))


def _fragment(confidence: float) -> OcrFragment:
    return OcrFragment(
        text="x", polygon=_POLY, confidence=confidence, low_confidence=False
    )


def test_flag_low_confidence_flags_strictly_below_threshold_only() -> None:
    fragments = (_fragment(0.5), _fragment(0.8), _fragment(0.95))
    flagged = flag_low_confidence(fragments, min_confidence=0.8)

    assert [f.low_confidence for f in flagged] == [True, False, False]


def test_flag_low_confidence_never_drops_a_fragment() -> None:
    """Flagging never filters (FR-002) -- a sub-threshold fragment still
    reaches the row model and the display."""
    fragments = tuple(_fragment(c) for c in (0.1, 0.99, 0.0, 1.0))
    flagged = flag_low_confidence(fragments, min_confidence=0.5)

    assert len(flagged) == len(fragments)
    assert [f.text for f in flagged] == [f.text for f in fragments]
    assert [f.confidence for f in flagged] == [f.confidence for f in fragments]


def test_flag_low_confidence_is_driven_by_the_threshold_argument() -> None:
    """Same fragment, different threshold -> different flag; the test
    supplies the threshold as input rather than asserting against the
    default constant (test-plan.md Risk #4's named anti-pattern)."""
    fragment = _fragment(0.85)

    assert (
        flag_low_confidence((fragment,), min_confidence=0.5)[0].low_confidence is False
    )
    assert (
        flag_low_confidence((fragment,), min_confidence=0.99)[0].low_confidence is True
    )
