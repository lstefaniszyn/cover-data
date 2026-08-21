from __future__ import annotations

import numpy as np

from cover_data.geometry.lines import detect_horizontal_lines, detect_vertical_lines

PAPER = 252
INK = 25


def _blank(w: int = 200, h: int = 150) -> np.ndarray:
    return np.full((h, w), PAPER, dtype=np.uint8)


def test_detects_a_long_horizontal_rule() -> None:
    img = _blank()
    img[60:62, 10:190] = INK  # a 2px-thick rule spanning most of the width

    lines = detect_horizontal_lines(img, min_length_frac=0.5)

    assert len(lines) == 1
    (line,) = lines
    assert line.y0 == line.y1 == 61 or 60 <= line.y0 <= 62
    assert line.x0 < 20
    assert line.x1 > 180


def test_detects_a_long_vertical_rule() -> None:
    img = _blank()
    img[10:140, 99:101] = INK

    lines = detect_vertical_lines(img, min_length_frac=0.5)

    assert len(lines) == 1
    (line,) = lines
    assert line.x0 == line.x1 or 99 <= line.x0 <= 101
    assert line.y0 < 20
    assert line.y1 > 130


def test_ignores_a_short_horizontal_segment_below_the_length_threshold() -> None:
    img = _blank()
    img[60:62, 80:120] = INK  # 40px of a 200px-wide page: 20%, below 50%

    lines = detect_horizontal_lines(img, min_length_frac=0.5)

    assert lines == []


def test_ignores_a_broad_soft_shadow_band_17png_style() -> None:
    """17.png's crease shadow is broad and soft, unlike a rule, which is
    thin and high-contrast -- the discriminator this test pins."""
    img = _blank()
    h, w = img.shape
    ys = np.arange(h).reshape(-1, 1).astype(float)
    y0 = 60.0
    sigma = 14.0  # a wide gradient, not a 2px hard edge
    profile = np.exp(-(((ys - y0) / sigma) ** 2))
    shade = 1.0 - 0.28 * np.broadcast_to(profile, (h, w))
    shadow = np.clip(np.asarray(img, dtype=np.float32) * shade, 0, 255).astype(np.uint8)

    lines = detect_horizontal_lines(shadow, min_length_frac=0.5)

    assert lines == []


def test_detects_a_rule_even_with_a_shadow_band_nearby() -> None:
    """A genuine rule must still be found when a soft shadow sits near it --
    the two adversaries (thin rule vs. broad shadow) are not mutually
    exclusive on a real page."""
    img = _blank()
    h, w = img.shape
    ys = np.arange(h).reshape(-1, 1).astype(float)
    profile = np.exp(-(((ys - 60.0) / 14.0) ** 2))
    shade = 1.0 - 0.28 * np.broadcast_to(profile, (h, w))
    img = np.clip(np.asarray(img, dtype=np.float32) * shade, 0, 255).astype(np.uint8)
    img[100:102, 10:190] = INK

    lines = detect_horizontal_lines(img, min_length_frac=0.5)

    assert len(lines) == 1
    assert 99 <= lines[0].y0 <= 103
