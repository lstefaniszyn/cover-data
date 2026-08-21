"""The coordinate contract between OCR preprocessing and the domain model.

Every coordinate leaving `ocr.paddle` must be in original, unresampled
source-image pixels (plan.md Phase 4 "Coordinate contract") -- document
unwarping and orientation correction improve what OCR reads, but must never
define the space geometry is recorded in, or S-03 redacts the wrong pixels.

PaddleOCR's document-orientation classifier can rotate the page by a coarse
angle (one of 0/90/180/270 degrees) before detection/recognition ever run.
That rotation is exactly invertible, and `OrientationTransform` does it.

Document *unwarping* (UVDoc) is deliberately left disabled at the engine
boundary (see `ocr.paddle`), precisely because it has no such contract: it
is a dense neural dewarp (confirmed against the installed
`paddlex.inference.models.image_unwarping` predictor, which returns only the
rectified image, never a forward or inverse coordinate map) with nothing
public to invert. Honoring "original source pixels" for a transform with no
exposed inverse is not possible, so it is not applied to the OCR call whose
coordinates this codebase trusts -- `use_doc_unwarping=False` is not an
oversight.
"""

from __future__ import annotations

from dataclasses import dataclass

from cover_data.domain import Point

VALID_ORIENTATION_ANGLES: tuple[int, ...] = (0, 90, 180, 270)


@dataclass(frozen=True)
class OrientationTransform:
    """The rotation PaddleOCR's orientation classifier applied before
    detection/recognition ran, and the source image's original (pre
    -rotation) size -- both needed to invert a point exactly.

    The four-case rotation formulas below are verified by
    `test_orientation_transform_round_trips_for_every_angle` as pure
    geometry; only `angle == 0` is exercised against a real OCR run in this
    fixture set (every generated fixture is a mild skew, not an actual
    90/180/270-degree page flip, so the classifier never reports otherwise
    here) -- the non-zero cases are correct by construction, not yet
    empirically confirmed against a real rotated scan.
    """

    angle: int
    source_width: float
    source_height: float

    def __post_init__(self) -> None:
        if self.angle not in VALID_ORIENTATION_ANGLES:
            raise ValueError(f"unsupported orientation angle: {self.angle}")

    @property
    def rotated_width(self) -> float:
        return self.source_height if self.angle in (90, 270) else self.source_width

    @property
    def rotated_height(self) -> float:
        return self.source_width if self.angle in (90, 270) else self.source_height

    def forward(self, point: Point) -> Point:
        """Map a point in original source pixels to where it lands after the
        classifier's rotation."""
        x, y = point.x, point.y
        w, h = self.source_width, self.source_height
        if self.angle == 0:
            return Point(x, y)
        if self.angle == 90:
            return Point(h - y, x)
        if self.angle == 180:
            return Point(w - x, h - y)
        return Point(y, w - x)  # 270

    def inverse(self, point: Point) -> Point:
        """Map a point in rotated space back to original source pixels --
        the direction every `OcrFragment` coordinate must go through before
        construction."""
        x, y = point.x, point.y
        w, h = self.source_width, self.source_height
        if self.angle == 0:
            return Point(x, y)
        if self.angle == 90:
            return Point(y, h - x)
        if self.angle == 180:
            return Point(w - x, h - y)
        return Point(w - y, x)  # 270
