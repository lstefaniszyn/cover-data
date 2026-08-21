"""The swappable OCR engine boundary.

Keeps Paddle, a future ONNX runtime, and Tesseract interchangeable behind one
`Protocol` (`context/foundation/tech-stack.md`'s develop-on-Paddle/
ship-on-ONNX plan depends on this not being a one-way door). Confidence
flagging lives here too, as a pure function over already-recognized
fragments, so it is testable without invoking any real engine and so a
caller (the CLI, in Phase 7) can re-flag the same fragments at a different
threshold without re-running OCR.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Final, Protocol

from cover_data.domain import OcrFragment

DEFAULT_MIN_CONFIDENCE: Final[float] = 0.80
"""Below this, a fragment is flagged low-confidence rather than trusted
silently (FR-002). 0.80 sits below the ~0.98+ scores PaddleOCR reports on
clean synthetic text and above the range a genuinely garbled read falls
into -- not calibrated against real degraded scans, since none exist yet
(see the PRD's blocking open question); revisit once one does."""


class OcrEngine(Protocol):
    """A single method, an image path in, fragments out -- every other
    detail (model directories, the installed library's result shape,
    preprocessing) is confined to one adapter module."""

    def recognize(self, image_path: Path) -> Sequence[OcrFragment]: ...


def flag_low_confidence(
    fragments: Sequence[OcrFragment], min_confidence: float
) -> tuple[OcrFragment, ...]:
    """Re-flag `fragments` at `min_confidence`, never dropping any of them --
    flagging never filters. Fragments are frozen, so this returns new
    instances rather than mutating the input."""
    return tuple(
        OcrFragment(
            text=f.text,
            polygon=f.polygon,
            confidence=f.confidence,
            low_confidence=f.confidence < min_confidence,
        )
        for f in fragments
    )
