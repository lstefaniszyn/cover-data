"""Ruling-line extraction: the strongest row/column-extent signal, present
on 25 of the 26 fixtures (plan.md Phase 5, "Ruling-line extraction").

Two adversaries are defended against explicitly, per the plan, rather than
by a threshold that happens to work:

- `17.png`'s crease shadow band is broad and soft; a genuine rule is thin
  and high-contrast. `_MAX_LINE_THICKNESS_PX` encodes that distinction
  directly, applied *after* morphological opening isolates long candidates
  -- a shadow band is long too, so length alone cannot reject it.
- `6.png`'s full-height vertical scan streaks pass any length-only test.
  Corroborating them against the header row's cell structure or detected
  text-column gaps is `geometry.columns`'s job; this module only reports
  candidate rule segments in original pixel coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import numpy.typing as npt

# A rule is a handful of pixels thick even after scan blur; a shadow band
# (17.png's crease) spans well over a dozen rows. Chosen with headroom
# between the two, not tuned to one fixture.
_MAX_LINE_THICKNESS_PX = 6

# Ink is expected to sit far below this; a soft photometric shade (a crease
# shadow, uneven lighting) should not cross it. This is a coarse first
# gate -- the thickness check above is what actually discriminates a rule
# from a broad shadow that does dip below it.
_INK_THRESHOLD = 200


@dataclass(frozen=True)
class LineSegment:
    """A candidate ruling-line segment in original source-image pixels."""

    x0: float
    y0: float
    x1: float
    y1: float


def _binarize(image: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    _, binary = cv2.threshold(image, _INK_THRESHOLD, 255, cv2.THRESH_BINARY_INV)
    return binary.astype(np.uint8)


def detect_horizontal_lines(
    image: npt.NDArray[np.uint8], min_length_frac: float
) -> list[LineSegment]:
    """Candidate horizontal rules at least `min_length_frac` of the image
    width, returned in original pixel coordinates."""
    _height, width = image.shape[:2]
    binary = _binarize(image)
    kernel_len = max(1, int(width * min_length_frac))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_len, 1))
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    num_labels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
        opened, connectivity=8
    )
    lines = []
    for label in range(1, num_labels):
        x, y, w, h, _area = stats[label]
        if h > _MAX_LINE_THICKNESS_PX or w < width * min_length_frac:
            continue
        mid_y = float(y) + float(h) / 2.0
        lines.append(LineSegment(x0=float(x), y0=mid_y, x1=float(x + w), y1=mid_y))
    return lines


def detect_vertical_lines(
    image: npt.NDArray[np.uint8], min_length_frac: float
) -> list[LineSegment]:
    """Candidate vertical rules at least `min_length_frac` of the image
    height, returned in original pixel coordinates."""
    height, _width = image.shape[:2]
    binary = _binarize(image)
    kernel_len = max(1, int(height * min_length_frac))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_len))
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    num_labels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
        opened, connectivity=8
    )
    lines = []
    for label in range(1, num_labels):
        x, y, w, h, _area = stats[label]
        if w > _MAX_LINE_THICKNESS_PX or h < height * min_length_frac:
            continue
        mid_x = float(x) + float(w) / 2.0
        lines.append(LineSegment(x0=mid_x, y0=float(y), x1=mid_x, y1=float(y + h)))
    return lines
