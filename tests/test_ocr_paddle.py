from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from cover_data.ocr.paddle import PaddleOcrEngine

FIXTURE_7 = Path("context/test_images/7.png")


@pytest.mark.slow
def test_paddle_engine_recognizes_fragments_over_fixture_7() -> None:
    """The real adapter, over a real fixture. Confirms empirically -- not by
    reading PaddleOCR's docs, which mix the 2.x and 3.x APIs -- that the
    installed 3.7.0 pipeline returns usable fragments through this adapter,
    and that every polygon coordinate lands back in the source image's
    bounds after the orientation-transform inversion."""
    width, height = Image.open(FIXTURE_7).size
    engine = PaddleOcrEngine()

    fragments = engine.recognize(FIXTURE_7)

    assert len(fragments) > 0
    for fragment in fragments:
        assert fragment.text.strip() != ""
        assert 0.0 <= fragment.confidence <= 1.0
        assert len(fragment.polygon) == 4
        for point in fragment.polygon:
            assert -1.0 <= point.x <= width + 1.0
            assert -1.0 <= point.y <= height + 1.0
