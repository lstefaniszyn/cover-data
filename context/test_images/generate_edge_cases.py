"""Generate the edge-case fixture scans for `context/test_images/`.

The original ladder (`1.png`-`6.png`) was image-model output: useful, but not
reproducible and carrying no ground truth. Everything numbered 7 and up is
produced by this script instead, so that:

* the exact row contents are known by construction (see `manifest.json`), which
  is what lets a test assert "row 4 is Anna Nowak" rather than eyeball it;
* a distortion can be dialled up or down and the fixture regenerated;
* the set stays free of real personal data.

Each fixture targets a named failure scenario from
`context/foundation/test-plan.md` section 2 (Risk Map) or an open question in
`context/foundation/roadmap.md`. The rationale per fixture lives in the
`FIXTURES` table at the bottom and is copied verbatim into `manifest.json`.

Run (Pillow/numpy are deliberately NOT project dependencies -- this is fixture
tooling, not product code):

    uv run --with pillow --with numpy --no-project \
        python context/test_images/generate_edge_cases.py

Add `--system-certs` to the `uv run` if the TLS-inspecting proxy is in play.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = Path(__file__).resolve().parent

# A4 at 150 dpi. Rendered at SS times this, distorted, then downsampled -- the
# downsample is what keeps the geometric warps from looking stair-stepped.
PAGE_W, PAGE_H = 1240, 1754
SS = 2

FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_ITALIC = "C:/Windows/Fonts/ariali.ttf"

PAPER = 252
INK = 25


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Person:
    """One debtor row, layout-independent."""

    lp: str
    imie: str
    nazwisko: str
    adres: tuple[str, ...]
    kwota: str
    wierzyciel: tuple[str, ...]

    @property
    def full_name(self) -> str:
        return f"{self.imie} {self.nazwisko}".strip()


@dataclass
class Column:
    header: tuple[str, ...]
    frac: float
    align: str = "left"


@dataclass
class Block:
    """A caption plus one bordered table."""

    columns: list[Column]
    rows: list[list[tuple[str, ...]]]
    caption: str = ""
    grid: bool = True


def _cell(value: str | Sequence[str]) -> tuple[str, ...]:
    return (value,) if isinstance(value, str) else tuple(value)


def layout_a(people: Sequence[Person]) -> Block:
    """`Lp.` + split given/family name, 6 columns (as in `1.png`, `3.png`)."""
    columns = [
        Column(("Lp.",), 0.06, "center"),
        Column(("Imię",), 0.12, "left"),
        Column(("Nazwisko",), 0.17, "left"),
        Column(("Adres zamieszkania",), 0.29, "left"),
        Column(("Kwota", "zadłużenia", "(PLN)"), 0.16, "right"),
        Column(("Wierzyciel",), 0.20, "left"),
    ]
    rows = [
        [
            _cell(p.lp),
            _cell(p.imie),
            _cell(p.nazwisko),
            _cell(p.adres),
            _cell(p.kwota),
            _cell(p.wierzyciel),
        ]
        for p in people
    ]
    return Block(columns=columns, rows=rows)


def layout_b(people: Sequence[Person]) -> Block:
    """`Lp.` + merged name, 5 columns (as in `2.png`, `4.png`, `6.png`)."""
    columns = [
        Column(("Lp.",), 0.06, "center"),
        Column(("Imię i nazwisko",), 0.25, "left"),
        Column(("Adres",), 0.29, "left"),
        Column(("Kwota", "zadłużenia", "(PLN)"), 0.17, "right"),
        Column(("Wierzyciel",), 0.23, "left"),
    ]
    rows = [
        [
            _cell(p.lp),
            _cell(p.full_name),
            _cell(p.adres),
            _cell(p.kwota),
            _cell(p.wierzyciel),
        ]
        for p in people
    ]
    return Block(columns=columns, rows=rows)


def layout_c(people: Sequence[Person]) -> Block:
    """No `Lp.`, split name, 5 columns (as in `5.png`)."""
    columns = [
        Column(("Imię",), 0.15, "left"),
        Column(("Nazwisko",), 0.19, "left"),
        Column(("Adres",), 0.31, "left"),
        Column(("Kwota", "zadłużenia", "(PLN)"), 0.16, "right"),
        Column(("Wierzyciel",), 0.19, "left"),
    ]
    rows = [
        [
            _cell(p.imie),
            _cell(p.nazwisko),
            _cell(p.adres),
            _cell(p.kwota),
            _cell(p.wierzyciel),
        ]
        for p in people
    ]
    return Block(columns=columns, rows=rows)


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


@dataclass
class Style:
    font_size: int = 17
    header_size: int = 17
    title_size: int = 22
    line_gap: int = 7
    cell_pad_x: int = 9
    cell_pad_y: int = 9
    grid_width: int = 2
    margin_x: int = 70
    top: int = 62
    table_top: int = 128


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size * SS)


def _text_h(font: ImageFont.FreeTypeFont) -> int:
    ascent, descent = font.getmetrics()
    return ascent + descent


def _draw_cell(
    draw: ImageDraw.ImageDraw,
    lines: Sequence[str],
    box: tuple[int, int, int, int],
    font: ImageFont.FreeTypeFont,
    align: str,
    style: Style,
) -> None:
    x0, y0, x1, _ = box
    line_h = _text_h(font) + style.line_gap * SS
    y = y0 + style.cell_pad_y * SS
    for line in lines:
        if not line:
            y += line_h
            continue
        w = int(draw.textlength(line, font=font))
        if align == "center":
            x = (x0 + x1) // 2 - w // 2
        elif align == "right":
            x = x1 - style.cell_pad_x * SS - w
        else:
            x = x0 + style.cell_pad_x * SS
        draw.text((x, y), line, font=font, fill=INK)
        y += line_h


def render_page(
    title: str,
    blocks: Sequence[Block],
    style: Style | None = None,
    page_w: int = PAGE_W,
    page_h: int = PAGE_H,
) -> Image.Image:
    """Render the page at SS times scale; callers downsample after warping."""
    style = style or Style()
    img = Image.new("L", (page_w * SS, page_h * SS), PAPER)
    draw = ImageDraw.Draw(img)

    body = _font(FONT_REGULAR, style.font_size)
    head = _font(FONT_BOLD, style.header_size)
    title_font = _font(FONT_BOLD, style.title_size)
    caption_font = _font(FONT_BOLD, style.font_size)

    draw.text((style.margin_x * SS, style.top * SS), title, font=title_font, fill=INK)

    table_w = (page_w - 2 * style.margin_x) * SS
    x_left = style.margin_x * SS
    y = style.table_top * SS
    line_h = _text_h(body) + style.line_gap * SS

    for block in blocks:
        if block.caption:
            draw.text((x_left, y), block.caption, font=caption_font, fill=INK)
            y += line_h + 6 * SS

        edges = [x_left]
        for col in block.columns:
            edges.append(edges[-1] + round(col.frac * table_w))

        table_y0 = y
        header_lines = max(len(c.header) for c in block.columns)
        header_h = header_lines * line_h + 2 * style.cell_pad_y * SS
        for idx, col in enumerate(block.columns):
            _draw_cell(
                draw,
                col.header,
                (edges[idx], y, edges[idx + 1], y + header_h),
                head,
                "center",
                style,
            )
        row_edges = [y, y + header_h]
        y += header_h

        for row in block.rows:
            n_lines = max(len(c) for c in row) if row else 1
            row_h = n_lines * line_h + 2 * style.cell_pad_y * SS
            for idx, (col, cell) in enumerate(zip(block.columns, row, strict=True)):
                _draw_cell(
                    draw,
                    cell,
                    (edges[idx], y, edges[idx + 1], y + row_h),
                    body,
                    col.align,
                    style,
                )
            y += row_h
            row_edges.append(y)

        if block.grid:
            gw = style.grid_width * SS
            for ry in row_edges:
                draw.line([(edges[0], ry), (edges[-1], ry)], fill=INK, width=gw)
            for ex in edges:
                draw.line([(ex, table_y0), (ex, row_edges[-1])], fill=INK, width=gw)

        y += 46 * SS

    return img


# --------------------------------------------------------------------------
# Distortions
# --------------------------------------------------------------------------


def _remap(img: Image.Image, dx: np.ndarray, dy: np.ndarray) -> Image.Image:
    arr = np.asarray(img, dtype=np.uint8)
    h, w = arr.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w]
    sx = np.clip(xs + dx, 0, w - 1).astype(np.int32)
    sy = np.clip(ys + dy, 0, h - 1).astype(np.int32)
    return Image.fromarray(arr[sy, sx])


def wave(
    img: Image.Image, amp: float, period: float, phase: float = 0.0, vert: float = 0.0
) -> Image.Image:
    """Page waviness: rows displaced horizontally as a function of y."""
    h, w = img.height, img.width
    ys = np.arange(h).reshape(-1, 1)
    xs = np.arange(w).reshape(1, -1)
    dx = amp * SS * np.sin(2 * math.pi * ys / (period * SS) + phase)
    dx = np.broadcast_to(dx, (h, w))
    dy = vert * SS * np.sin(2 * math.pi * xs / (period * 1.7 * SS) + phase)
    dy = np.broadcast_to(dy, (h, w))
    return _remap(img, dx, dy)


def fold(img: Image.Image, y_frac: float, strength: float) -> Image.Image:
    """A crease: local vertical pinch plus a soft shadow band across the page."""
    h, w = img.height, img.width
    ys = np.arange(h).reshape(-1, 1).astype(float)
    y0 = y_frac * h
    sigma = 0.045 * h
    profile = np.exp(-(((ys - y0) / sigma) ** 2))
    dy = np.broadcast_to(-strength * SS * profile, (h, w))
    dx = np.zeros((h, w))
    warped = _remap(img, dx, dy)

    arr = np.asarray(warped, dtype=np.float32)
    shade = 1.0 - 0.28 * np.broadcast_to(profile, (h, w))
    arr = np.clip(arr * shade, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def rotate(img: Image.Image, deg: float, fill: int = PAPER) -> Image.Image:
    return img.rotate(deg, resample=Image.Resampling.BICUBIC, fillcolor=fill)


def _perspective_coeffs(
    src: Sequence[tuple[float, float]], dst: Sequence[tuple[float, float]]
) -> list[float]:
    rows: list[list[float]] = []
    for (x, y), (u, v) in zip(dst, src, strict=True):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    a = np.array(rows, dtype=float)
    b = np.array(src, dtype=float).reshape(8)
    return list(np.linalg.solve(a, b))


def perspective(img: Image.Image, quad: Sequence[tuple[float, float]]) -> Image.Image:
    """Warp so the page corners land on `quad` (fractions of width/height)."""
    w, h = img.width, img.height
    src = [(0.0, 0.0), (float(w), 0.0), (float(w), float(h)), (0.0, float(h))]
    dst = [(fx * w, fy * h) for fx, fy in quad]
    coeffs = _perspective_coeffs(src, dst)
    return img.transform(
        (w, h),
        Image.Transform.PERSPECTIVE,
        coeffs,
        resample=Image.Resampling.BICUBIC,
        fillcolor=PAPER,
    )


def lighting(
    img: Image.Image, cx: float = 0.3, cy: float = 0.2, depth: float = 0.45
) -> Image.Image:
    """Uneven illumination: a bright spot falling off across the page."""
    h, w = img.height, img.width
    ys = np.linspace(0, 1, h).reshape(-1, 1)
    xs = np.linspace(0, 1, w).reshape(1, -1)
    d = np.sqrt((xs - cx) ** 2 + ((ys - cy) * 1.25) ** 2)
    gain = 1.0 - depth * np.clip(d / 1.15, 0, 1)
    arr = np.asarray(img, dtype=np.float32) * gain
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def contrast(img: Image.Image, gain: float, offset: float) -> Image.Image:
    arr = np.asarray(img, dtype=np.float32)
    arr = (arr - 128.0) * gain + 128.0 + offset
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def blur(img: Image.Image, radius: float) -> Image.Image:
    return img.filter(ImageFilter.GaussianBlur(radius))


def noise(img: Image.Image, sigma: float, seed: int, salt: float = 0.0) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = np.asarray(img, dtype=np.float32)
    arr = arr + rng.normal(0, sigma, arr.shape)
    if salt > 0:
        mask = rng.random(arr.shape)
        arr[mask < salt / 2] = 0
        arr[mask > 1 - salt / 2] = 255
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def scanlines(img: Image.Image, period: int, strength: float, seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    h, w = img.height, img.width
    arr = np.asarray(img, dtype=np.float32)
    ys = np.arange(h).reshape(-1, 1)
    band = 1.0 - strength * (np.sin(2 * math.pi * ys / period) > 0.72)
    arr = arr * band
    for _ in range(6):
        y = int(rng.integers(0, h))
        arr[y : y + int(rng.integers(1, 3)), :] *= float(rng.uniform(0.35, 0.7))
    for _ in range(3):
        x = int(rng.integers(0, w))
        arr[:, x : x + 2] *= 0.55
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def jpegify(img: Image.Image, quality: int) -> Image.Image:
    buf = BytesIO()
    img.convert("L").save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("L")


def punch_holes(img: Image.Image, count: int = 3) -> Image.Image:
    out = img.convert("L")
    draw = ImageDraw.Draw(out)
    h, w = out.height, out.width
    r = int(0.017 * w)
    xs = int(0.035 * w)
    for i in range(count):
        cy = int(h * (0.28 + 0.22 * i))
        draw.ellipse([xs - r, cy - r, xs + r, cy + r], fill=60)
        draw.arc([xs - r, cy - r, xs + r, cy + r], 200, 340, fill=140, width=3)
    return out


def scanner_border(img: Image.Image, pad: int = 26, level: int = 32) -> Image.Image:
    """Lid-open scan: the page floats on a dark background."""
    out = Image.new("L", (img.width + 2 * pad, img.height + 2 * pad), level)
    out.paste(img, (pad, pad))
    return out.resize((img.width, img.height), Image.Resampling.LANCZOS)


def stamp(
    img: Image.Image, text: str, at: tuple[float, float], angle: float = 14.0
) -> Image.Image:
    """A rubber stamp landing across rows -- ink that is not table content."""
    base = img.convert("L")
    layer = Image.new("L", (int(base.width * 0.42), int(base.height * 0.10)), 255)
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(
        [4, 4, layer.width - 5, layer.height - 5], radius=14, outline=70, width=6
    )
    font = ImageFont.truetype(FONT_BOLD, int(layer.height * 0.42))
    tw = int(d.textlength(text, font=font))
    d.text(
        ((layer.width - tw) // 2, int(layer.height * 0.28)), text, font=font, fill=70
    )
    layer = layer.rotate(
        angle, expand=True, resample=Image.Resampling.BICUBIC, fillcolor=255
    )
    pos = (int(at[0] * base.width), int(at[1] * base.height))
    region = base.crop((pos[0], pos[1], pos[0] + layer.width, pos[1] + layer.height))
    arr = np.minimum(
        np.asarray(region, dtype=np.float32),
        np.asarray(layer, dtype=np.float32) * 0.55 + 255 * 0.45,
    )
    base.paste(Image.fromarray(arr.astype(np.uint8)), pos)
    return base


def handwriting(img: Image.Image, seed: int) -> Image.Image:
    """A biro annotation crossing several row boundaries."""
    out = img.convert("L")
    d = ImageDraw.Draw(out)
    rng = np.random.default_rng(seed)
    w, h = out.width, out.height
    font = ImageFont.truetype(FONT_ITALIC, int(0.022 * h))
    d.text((int(0.60 * w), int(0.34 * h)), "zapłacone 12.03", font=font, fill=95)
    pts = []
    for i in range(26):
        t = i / 25
        x = 0.18 * w + t * 0.66 * w
        y = 0.46 * h + 0.075 * h * math.sin(t * 5.2) + rng.normal(0, 2.0)
        pts.append((x, y))
    d.line(pts, fill=95, width=3, joint="curve")
    d.line(
        [(0.62 * w, 0.30 * h), (0.66 * w, 0.355 * h)],
        fill=95,
        width=3,
    )
    return out


def downsample(img: Image.Image, w: int, h: int) -> Image.Image:
    return img.resize((w, h), Image.Resampling.LANCZOS)


def fit_page(img: Image.Image, margin: int = 70) -> Image.Image:
    """Trim the sheet to its content plus a margin.

    Keeps the framing close to the original `1.png`-`6.png` set, and — more
    importantly — makes page fractions meaningful: 0.5 of the sheet is now
    somewhere in the table rather than in empty paper below it.
    """
    arr = np.asarray(img)
    inked = np.where(arr.min(axis=1) < 200)[0]
    if inked.size == 0:
        return img
    bottom = min(int(inked.max()) + margin * SS, img.height)
    return img.crop((0, 0, img.width, bottom))


# --------------------------------------------------------------------------
# Row pools -- placeholder names only, no real personal data
# --------------------------------------------------------------------------


def people(rows: Sequence[tuple[str, str, str, str, str, str]]) -> list[Person]:
    return [
        Person(
            lp=str(i + 1),
            imie=imie,
            nazwisko=nazwisko,
            adres=(a1, a2),
            kwota=kwota,
            wierzyciel=tuple(w.split("|")),
        )
        for i, (imie, nazwisko, a1, a2, kwota, w) in enumerate(rows)
    ]


BASE = people(
    [
        (
            "Jan",
            "Kowalski",
            "ul. Słoneczna 12/3",
            "00-001 Warszawa",
            "1 250,00",
            "ABC Sp. z o.o.",
        ),
        ("Anna", "Nowak", "ul. Zielona 5/7", "30-002 Kraków", "980,50", "XYZ S.A."),
        (
            "Piotr",
            "Wiśniewski",
            "ul. Leśna 8",
            "80-123 Gdańsk",
            "2 450,00",
            "Delta Polska|Sp. z o.o.",
        ),
        (
            "Katarzyna",
            "Wójcik",
            "ul. Kwiatowa 3/1",
            "60-101 Poznań",
            "1 100,00",
            "Bank Fikcyjny S.A.",
        ),
        (
            "Mariusz",
            "Kamiński",
            "ul. Polna 15",
            "20-400 Lublin",
            "750,00",
            "Omega Telekom|S.A.",
        ),
        (
            "Paulina",
            "Lewandowska",
            "ul. Długa 11/5",
            "50-001 Wrocław",
            "1 870,00",
            "Sigma Bank S.A.",
        ),
        (
            "Tomasz",
            "Zieliński",
            "ul. Bukowa 9",
            "40-200 Katowice",
            "2 150,00",
            "Plus Fikcja S.A.",
        ),
        (
            "Justyna",
            "Mazur",
            "ul. Spokojna 2",
            "85-200 Bydgoszcz",
            "620,00",
            "Kappa Kredyt|Sp. z o.o.",
        ),
    ]
)


POOL: list[tuple[str, str]] = [
    ("Adam", "Adamczyk"),
    ("Beata", "Borowska"),
    ("Cezary", "Cichoń"),
    ("Dorota", "Dąbrowska"),
    ("Emil", "Ergiet"),
    ("Filip", "Fabiański"),
    ("Grażyna", "Górska"),
    ("Henryk", "Hajduk"),
    ("Irena", "Iwańska"),
    ("Jakub", "Jasiński"),
    ("Karol", "Krupa"),
    ("Lidia", "Lisowska"),
    ("Marek", "Maj"),
    ("Natalia", "Nowicka"),
    ("Oskar", "Olszewski"),
    ("Patryk", "Pawlak"),
    ("Renata", "Rutkowska"),
    ("Sylwia", "Sowa"),
    ("Tadeusz", "Tomczyk"),
    ("Urszula", "Urban"),
    ("Wanda", "Wrona"),
    ("Zenon", "Zawadzki"),
]


def filler(count: int, start: int = 0) -> list[Person]:
    """`count` distinct debtors drawn from POOL — never a repeated name."""
    picked = POOL[start : start + count]
    assert len(picked) == count, "POOL exhausted; add more names"
    return [
        Person(
            "",
            imie,
            nazw,
            (f"ul. Przykładowa {i + 1}", f"{10 + i:02d}-{100 + i:03d} Miastowo"),
            f"{(i + 3) * 137},{(i * 7) % 100:02d}",
            ("ABC Sp. z o.o.",) if i % 2 else ("XYZ S.A.",),
        )
        for i, (imie, nazw) in enumerate(picked, start=start)
    ]


def renumber(persons: Sequence[Person]) -> list[Person]:
    return [
        Person(str(i + 1), p.imie, p.nazwisko, p.adres, p.kwota, p.wierzyciel)
        for i, p in enumerate(persons)
    ]


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@dataclass
class Fixture:
    filename: str
    label: str
    title: str
    layout: str
    targets: list[str]
    distortion: str
    why: str
    scenarios: list[dict[str, Any]]
    build: Callable[[], tuple[Image.Image, list[Person]]]
    people: list[Person] = field(default_factory=list)
    size_px: tuple[int, int] = (PAGE_W, PAGE_H)
    notes: str = ""


def _finish(img: Image.Image, width: int | None = None) -> Image.Image:
    """Downsample the supersampled sheet. `width` forces a final pixel width
    (used by the deliberately low-resolution fixture) and keeps aspect."""
    if width is None:
        return downsample(img, img.width // SS, img.height // SS)
    return downsample(img, width, round(width * img.height / img.width))


def f07() -> tuple[Image.Image, list[Person]]:
    persons = renumber(
        [
            BASE[0],
            BASE[1],
            BASE[2],
            Person(
                "",
                "Anna",
                "Nowak-Kowalska",
                ("ul. Miodowa 4", "31-055 Kraków"),
                "1 405,00",
                ("Sigma Bank S.A.",),
            ),
            BASE[4],
            Person(
                "",
                "Anna",
                "Nowak",
                ("ul. Wąska 18/2", "70-410 Szczecin"),
                "3 010,00",
                ("Kappa Kredyt", "Sp. z o.o."),
            ),
            BASE[6],
            Person(
                "",
                "Anna",
                "Nowakowska",
                ("ul. Cicha 6", "41-200 Sosnowiec"),
                "515,00",
                ("ABC Sp. z o.o.",),
            ),
        ]
    )
    img = fit_page(
        render_page("Przykład 7 – Zduplikowane imiona i nazwiska", [layout_a(persons)])
    )
    return _finish(rotate(img, -0.6)), persons


def f08() -> tuple[Image.Image, list[Person]]:
    persons = renumber(
        [
            Person(
                "",
                "Jan",
                "Kowalski",
                ("ul. Słoneczna 12/3", "00-001 Warszawa"),
                "1 250,00",
                ("ABC Sp. z o.o.",),
            ),
            Person(
                "",
                "Janina",
                "Kowalska",
                ("ul. Słoneczna 12/4", "00-001 Warszawa"),
                "640,00",
                ("ABC Sp. z o.o.",),
            ),
            Person(
                "",
                "Jan",
                "Kowalski-Nowak",
                ("ul. Morska 21", "81-001 Gdynia"),
                "2 090,00",
                ("Sigma Bank S.A.",),
            ),
            Person(
                "",
                "Jan",
                "Kowal",
                ("ul. Krótka 3", "10-100 Olsztyn"),
                "310,00",
                ("XYZ S.A.",),
            ),
            Person(
                "",
                "Jan",
                "Kowalewski",
                ("ul. Lipowa 7/2", "35-020 Rzeszów"),
                "1 775,00",
                ("Delta Polska", "Sp. z o.o."),
            ),
            Person(
                "",
                "Adam",
                "Kowalski",
                ("ul. Wiosenna 9", "15-300 Białystok"),
                "890,00",
                ("Omega Telekom", "S.A."),
            ),
            Person(
                "",
                "Jan",
                "Nowak",
                ("ul. Sosnowa 14", "26-600 Radom"),
                "1 040,00",
                ("Bank Fikcyjny S.A.",),
            ),
            Person(
                "",
                "Joanna",
                "Kowalczyk",
                ("ul. Rzeczna 2/8", "87-100 Toruń"),
                "2 330,00",
                ("Kappa Kredyt", "Sp. z o.o."),
            ),
        ]
    )
    img = fit_page(
        render_page(
            "Przykład 8 – Nazwiska podobne i zawierające się w sobie",
            [layout_a(persons)],
        )
    )
    return _finish(noise(img, 3.5, seed=8)), persons


def f09() -> tuple[Image.Image, list[Person]]:
    persons = renumber(
        [
            Person(
                "",
                "Łukasz",
                "Żółciński",
                ("ul. Świętokrzyska 8/3", "00-020 Warszawa"),
                "1 460,00",
                ("ABC Sp. z o.o.",),
            ),
            Person(
                "",
                "Zofia",
                "Ćwiklińska",
                ("ul. Łąkowa 21", "61-004 Poznań"),
                "705,00",
                ("Sigma Bank S.A.",),
            ),
            Person(
                "",
                "Michał",
                "Świątkowski",
                ("ul. Żeromskiego 4", "26-600 Radom"),
                "2 890,00",
                ("XYZ S.A.",),
            ),
            Person(
                "",
                "Agnieszka",
                "Źrałek",
                ("ul. Miła 17/9", "31-035 Kraków"),
                "1 120,00",
                ("Delta Polska", "Sp. z o.o."),
            ),
            Person(
                "",
                "Grzegorz",
                "Gąsiorek",
                ("ul. Dąbrowskiego 55", "42-200 Częstochowa"),
                "430,00",
                ("Omega Telekom", "S.A."),
            ),
            Person(
                "",
                "Jędrzej",
                "Wąsowicz",
                ("ul. Ćmielowska 6", "27-400 Ostrowiec"),
                "1 995,00",
                ("Bank Fikcyjny S.A.",),
            ),
            Person(
                "",
                "Małgorzata",
                "Ścibor-Rylska",
                ("ul. Poniatowskiego 3", "20-060 Lublin"),
                "3 250,00",
                ("Kappa Kredyt", "Sp. z o.o."),
            ),
            Person(
                "",
                "Sławomir",
                "Łęcki",
                ("ul. Ogińskiego 12", "85-092 Bydgoszcz", "m. 4"),
                "860,00",
                ("Plus Fikcja S.A.",),
            ),
        ]
    )
    img = fit_page(
        render_page(
            "Przykład 9 – Polskie znaki diakrytyczne w nazwiskach", [layout_a(persons)]
        )
    )
    return _finish(noise(blur(img, 0.9), 4.0, seed=9)), persons


def f10() -> tuple[Image.Image, list[Person]]:
    persons = renumber(
        [
            Person(
                "",
                "Jan",
                "Kowalewski",
                ("ul. Lipowa 7/2", "35-020 Rzeszów"),
                "1 775,00",
                ("ABC Sp. z o.o.",),
            ),
            Person(
                "",
                "Janusz",
                "Kowalik",
                ("ul. Polna 5", "20-400 Lublin"),
                "615,00",
                ("XYZ S.A.",),
            ),
            Person(
                "",
                "Jan",
                "Kowalczewski",
                ("ul. Górna 18", "58-100 Świdnica"),
                "2 240,00",
                ("Sigma Bank S.A.",),
            ),
            Person(
                "",
                "Iwona",
                "Kowalska-Bąk",
                ("ul. Nowa 3/11", "44-100 Gliwice"),
                "980,00",
                ("Delta Polska", "Sp. z o.o."),
            ),
            Person(
                "",
                "Marek",
                "Kowal",
                ("ul. Stara 22", "05-800 Pruszków"),
                "1 330,00",
                ("Omega Telekom", "S.A."),
            ),
            Person(
                "",
                "Halina",
                "Kowalczyk",
                ("ul. Wesoła 8", "63-400 Ostrów Wlkp.", "m. 2"),
                "455,00",
                ("Bank Fikcyjny S.A.",),
            ),
            Person(
                "",
                "Jan",
                "Kowalów",
                ("ul. Piaskowa 30", "97-200 Tomaszów"),
                "3 105,00",
                ("Kappa Kredyt", "Sp. z o.o."),
            ),
            Person(
                "",
                "Bożena",
                "Kowalewicz",
                ("ul. Akacjowa 1/6", "77-300 Człuchów"),
                "720,00",
                ("Plus Fikcja S.A.",),
            ),
        ]
    )
    img = fit_page(
        render_page("Przykład 10 – Brak szukanej osoby na liście", [layout_b(persons)])
    )
    return _finish(rotate(img, 0.9)), persons


def f11() -> tuple[Image.Image, list[Person]]:
    img = fit_page(
        render_page("Przykład 11 – Silne pofalowanie strony", [layout_a(BASE)])
    )
    img = wave(img, amp=19, period=310, phase=0.7, vert=7)
    img = wave(img, amp=6, period=97, phase=2.1)
    img = lighting(img, cx=0.5, cy=0.4, depth=0.22)
    return _finish(noise(img, 3.0, seed=11)), BASE


def f12() -> tuple[Image.Image, list[Person]]:
    img = fit_page(
        render_page("Przykład 12 – Mocne przekrzywienie skanu", [layout_b(BASE)])
    )
    img = rotate(img, -6.8)
    img = scanner_border(img, pad=30 * SS, level=28)
    img = _finish(img)
    return noise(img, 4.5, seed=12), BASE


def f13() -> tuple[Image.Image, list[Person]]:
    img = fit_page(
        render_page("Przykład 13 – Zdjęcie telefonem, perspektywa", [layout_a(BASE)])
    )
    img = perspective(
        img, [(0.055, 0.035), (0.968, 0.008), (0.995, 0.972), (0.012, 0.995)]
    )
    img = rotate(img, 1.4)
    img = lighting(img, cx=0.72, cy=0.12, depth=0.5)
    img = _finish(img)
    return noise(blur(img, 0.7), 4.0, seed=13), BASE


def f14() -> tuple[Image.Image, list[Person]]:
    persons = renumber(
        [
            Person(
                "",
                "Jan",
                "Kowalski",
                ("ul. Słoneczna 12/3", "00-001 Warszawa"),
                "1 250,00",
                ("ABC Sp. z o.o.",),
            ),
            Person(
                "",
                "Anna",
                "Nowak",
                ("Osiedle Przyjaźni 14A", "bud. 3, klatka II, m. 27", "30-002 Kraków"),
                "980,50",
                ("XYZ S.A.", "Oddział Kraków"),
            ),
            Person(
                "",
                "Piotr",
                "Wiśniewski",
                ("ul. Leśna 8", "80-123 Gdańsk"),
                "2 450,00",
                ("Delta Polska",),
            ),
            Person(
                "",
                "Katarzyna",
                "Wójcik",
                ("ul. Generała Władysława", "Sikorskiego 118/240", "60-101 Poznań"),
                "1 100,00",
                ("Bank Fikcyjny S.A.", "Centrum Windykacji", "Oddział Zachód"),
            ),
            Person(
                "",
                "Mariusz",
                "Kamiński",
                ("ul. Polna 15", "20-400 Lublin"),
                "750,00",
                ("Omega Telekom",),
            ),
            Person(
                "",
                "Paulina",
                "Lewandowska",
                (
                    "ul. Marszałka Józefa",
                    "Piłsudskiego 3/17",
                    "50-001 Wrocław",
                    "(dawniej ul. Nowa 3)",
                ),
                "1 870,00",
                ("Sigma Bank S.A.",),
            ),
            Person(
                "",
                "Tomasz",
                "Zieliński",
                ("ul. Bukowa 9", "40-200 Katowice"),
                "2 150,00",
                ("Plus Fikcja S.A.",),
            ),
            Person(
                "",
                "Justyna",
                "Mazur",
                ("ul. Spokojna 2", "85-200 Bydgoszcz"),
                "620,00",
                ("Kappa Kredyt",),
            ),
        ]
    )
    img = fit_page(
        render_page(
            "Przykład 14 – Wiersze o bardzo różnej wysokości", [layout_a(persons)]
        )
    )
    return _finish(rotate(noise(img, 3.0, seed=14), -0.8)), persons


def f15() -> tuple[Image.Image, list[Person]]:
    persons = renumber(filler(len(POOL)))
    style = Style(font_size=12, header_size=12, line_gap=3, cell_pad_y=4, cell_pad_x=6)
    img = fit_page(
        render_page(
            "Przykład 15 – Gęsta tabela, 22 wiersze, mały odstęp",
            [layout_b(persons)],
            style=style,
        )
    )
    img = wave(img, amp=4, period=220, phase=0.3)
    return _finish(noise(img, 3.5, seed=15)), persons


def f16() -> tuple[Image.Image, list[Person]]:
    block = layout_c(BASE)
    block.grid = False
    img = fit_page(
        render_page(
            "Przykład 16 – Tabela bez linii siatki (kolumny na spacjach)", [block]
        )
    )
    img = rotate(img, 1.7)
    return _finish(noise(img, 3.0, seed=16)), BASE


def f17() -> tuple[Image.Image, list[Person]]:
    img = fit_page(
        render_page("Przykład 17 – Zagięcie kartki i cień na zgięciu", [layout_a(BASE)])
    )
    img = fold(img, y_frac=0.52, strength=13)
    img = wave(img, amp=5, period=430, phase=1.1)
    img = lighting(img, cx=0.35, cy=0.15, depth=0.25)
    return _finish(noise(img, 3.5, seed=17)), BASE


def f18() -> tuple[Image.Image, list[Person]]:
    # Deliberately NOT fit_page()'d: more rows are laid out than the sheet can
    # hold, so the table runs off the bottom edge and the last row has no
    # closing rule. That missing boundary is the whole point of the fixture.
    persons = renumber(list(BASE) + filler(18))
    style = Style(top=30, table_top=74)
    img = render_page(
        "Przykład 18 – Tabela ucięta u dołu strony", [layout_a(persons)], style=style
    )
    img = rotate(img, -1.1)
    return _finish(noise(img, 3.0, seed=18)), persons


def f19() -> tuple[Image.Image, list[Person]]:
    persons = renumber([BASE[3]])
    img = fit_page(
        render_page("Przykład 19 – Tabela z jednym wierszem", [layout_a(persons)])
    )
    return _finish(noise(rotate(img, 0.7), 3.0, seed=19)), persons


def f20() -> tuple[Image.Image, list[Person]]:
    block = layout_a([])
    img = fit_page(render_page("Przykład 20 – Tabela bez wierszy danych", [block]))
    return _finish(noise(img, 3.0, seed=20)), []


def f21() -> tuple[Image.Image, list[Person]]:
    persons = [
        Person(
            "1",
            "Jan",
            "Kowalski",
            ("ul. Słoneczna 12/3", "00-001 Warszawa"),
            "1 250,00",
            ("ABC Sp. z o.o.",),
        ),
        Person("2", "Anna", "Nowak", ("",), "980,50", ("XYZ S.A.",)),
        Person(
            "",
            "Piotr",
            "Wiśniewski",
            ("ul. Leśna 8", "80-123 Gdańsk"),
            "2 450,00",
            ("",),
        ),
        Person(
            "4",
            "",
            "Wójcik",
            ("ul. Kwiatowa 3/1", "60-101 Poznań"),
            "",
            ("Bank Fikcyjny S.A.",),
        ),
        Person(
            "5",
            "Mariusz",
            "Kamiński",
            ("ul. Polna 15", "20-400 Lublin"),
            "750,00",
            ("Omega Telekom",),
        ),
        Person("6", "", "", ("", ""), "", ("",)),
        Person(
            "7",
            "Tomasz",
            "Zieliński",
            ("brak danych", ""),
            "2 150,00",
            ("Plus Fikcja S.A.",),
        ),
        Person(
            "8",
            "Justyna",
            "Mazur",
            ("ul. Spokojna 2", "85-200 Bydgoszcz"),
            "620,00",
            ("Kappa Kredyt",),
        ),
    ]
    img = fit_page(
        render_page("Przykład 21 – Puste komórki i brakujące dane", [layout_a(persons)])
    )
    return _finish(noise(img, 3.0, seed=21)), persons


def f22() -> tuple[Image.Image, list[Person]]:
    img = fit_page(
        render_page(
            "Przykład 22 – Pieczątka, dopisek odręczny, dziurkacz", [layout_a(BASE)]
        )
    )
    img = _finish(img)
    img = stamp(img, "DO WINDYKACJI", at=(0.34, 0.30), angle=13)
    img = handwriting(img, seed=22)
    img = punch_holes(img, count=3)
    img = lighting(img, cx=0.4, cy=0.3, depth=0.18)
    return noise(img, 3.5, seed=222), BASE


def f23() -> tuple[Image.Image, list[Person]]:
    # Both tables number their rows from 1 on the page; the manifest keeps them
    # distinguishable as A1..A4 / B1..B4 so "row 1" is never ambiguous.
    top = renumber(BASE[:4])
    bottom = renumber(BASE[4:])
    first = layout_a(top)
    first.caption = "Tabela A – wierzyciel ABC Sp. z o.o."
    second = layout_a(bottom)
    second.caption = "Tabela B – wierzyciel Sigma Bank S.A. (cd.)"
    img = fit_page(
        render_page("Przykład 23 – Dwie tabele na jednej stronie", [first, second])
    )
    img = rotate(img, -1.3)
    persons = [
        Person(f"{tag}{p.lp}", p.imie, p.nazwisko, p.adres, p.kwota, p.wierzyciel)
        for tag, group in (("A", top), ("B", bottom))
        for p in group
    ]
    return _finish(noise(img, 3.0, seed=23)), persons


def f24() -> tuple[Image.Image, list[Person]]:
    img = fit_page(
        render_page("Przykład 24 – Blada kserokopia, artefakty JPEG", [layout_b(BASE)])
    )
    # Tuned to be *marginal*, not illegible: a human can still read the rows
    # with effort, so a wrong OCR read here is a real defect rather than an
    # unavoidable one. That is what makes it a test of FR-002 flagging.
    img = _finish(img, width=760)
    img = contrast(img, gain=0.55, offset=26)
    img = lighting(img, cx=0.2, cy=0.8, depth=0.22)
    img = blur(img, 0.6)
    img = jpegify(img, quality=30)
    return noise(img, 3.5, seed=24, salt=0.0006), BASE


FIXTURES: list[Fixture] = [
    Fixture(
        filename="7.png",
        label="Przykład 7",
        title="Zduplikowane imiona i nazwiska",
        layout="A",
        targets=["Anna Nowak"],
        distortion="lekkie pochylenie (-0.6°)",
        why=(
            "Risk #6 (silent auto-pick). Two rows carry the identical name "
            "'Anna Nowak' (rows 2 and 6) alongside two near-misses "
            "('Anna Nowak-Kowalska', 'Anna Nowakowska'). FR-006 requires "
            "explicit confirmation here; auto-picking either row is a defect."
        ),
        scenarios=[
            {
                "query": "Anna Nowak",
                "expected_matches": 2,
                "expected_rows": [2, 6],
                "must": "require confirmation (FR-006)",
            },
            {
                "query": "Anna Nowakowska",
                "expected_matches": 1,
                "expected_rows": [8],
                "must": "proceed without prompting",
            },
        ],
        build=f07,
    ),
    Fixture(
        filename="8.png",
        label="Przykład 8",
        title="Nazwiska podobne i zawierające się w sobie",
        layout="A",
        targets=["Jan Kowalski"],
        distortion="szum gaussowski",
        why=(
            "FR-005 exact-match. 'Jan Kowalski' is a strict prefix of "
            "'Jan Kowalski-Nowak' and shares a stem with Kowalska / Kowal / "
            "Kowalewski / Kowalczyk. A substring or fuzzy matcher hits 2+ rows; "
            "exact match must hit exactly one. Redacting the wrong one exposes "
            "a different debtor."
        ),
        scenarios=[
            {
                "query": "Jan Kowalski",
                "expected_matches": 1,
                "expected_rows": [1],
                "must": "not match row 3 (Kowalski-Nowak)",
            },
            {
                "query": "Kowalski",
                "expected_matches": 0,
                "expected_rows": [],
                "must": "surname-only query is not an exact full-name match",
            },
        ],
        build=f08,
    ),
    Fixture(
        filename="9.png",
        label="Przykład 9",
        title="Polskie znaki diakrytyczne w nazwiskach",
        layout="A",
        targets=["Łukasz Żółciński"],
        distortion="lekkie rozmycie + szum",
        why=(
            "Risk #4 (low-confidence OCR flowing through unflagged). Every row "
            "carries diacritics that Tesseract routinely folds (ł→l, ż→z, ą→a, "
            "ś→s, ć→c). Exact match against a query typed with diacritics fails "
            "silently if the OCR fold is not surfaced as low confidence."
        ),
        scenarios=[
            {
                "query": "Łukasz Żółciński",
                "expected_matches": 1,
                "expected_rows": [1],
                "must": "match despite OCR diacritic folding, or flag low confidence rather than report 0 matches",
            },
            {
                "query": "Lukasz Zolcinski",
                "expected_matches": 0,
                "expected_rows": [],
                "must": "documented decision: is the de-diacriticised query a match? Currently expected NOT to be under strict exact-match",
            },
        ],
        build=f09,
    ),
    Fixture(
        filename="10.png",
        label="Przykład 10",
        title="Brak szukanej osoby na liście",
        layout="B",
        targets=[],
        distortion="lekkie pochylenie (+0.9°)",
        why=(
            "The zero-match path. Every surname is a near-miss on 'Jan Kowalski' "
            "(Kowalewski, Kowalik, Kowalczewski, Kowalów, Kowal) but none equals "
            "it. The tool must report no match and write no output file — never "
            "fall back to the closest row."
        ),
        scenarios=[
            {
                "query": "Jan Kowalski",
                "expected_matches": 0,
                "expected_rows": [],
                "must": "report no match, produce no output PDF",
            },
        ],
        build=f10,
    ),
    Fixture(
        filename="11.png",
        label="Przykład 11",
        title="Silne pofalowanie strony",
        layout="A",
        targets=["Katarzyna Wójcik"],
        distortion="fala pozioma amp. 19px + fala 6px + nierówne światło",
        why=(
            "Risks #1 and #2, at the amplitude `3.png` was judged too mild for "
            "(test-plan §2 finding 2). Row baselines are no longer straight "
            "lines, so a redaction band computed from a horizontal rectangle "
            "either clips the target row or leaves a neighbour's strip visible."
        ),
        scenarios=[
            {
                "query": "Katarzyna Wójcik",
                "expected_matches": 1,
                "expected_rows": [4],
                "must": "band follows the wavy row boundary; no pixel of rows 3 or 5 survives, no pixel of row 4 is lost",
            },
        ],
        build=f11,
    ),
    Fixture(
        filename="12.png",
        label="Przykład 12",
        title="Mocne przekrzywienie skanu i ciemne marginesy",
        layout="B",
        targets=["Tomasz Zieliński"],
        distortion="obrót -6.8° + ciemne tło skanera",
        why=(
            "Deskew must run before row detection. At -6.8° a row spans ~130px "
            "vertically across the page width. The dark scanner border is the "
            "second half of the trap: page-extent detection that keys on the "
            "darkest pixels finds the border, not the paper."
        ),
        scenarios=[
            {
                "query": "Tomasz Zieliński",
                "expected_matches": 1,
                "expected_rows": [7],
                "must": "deskew before band placement; dark border must not be read as content",
            },
        ],
        build=f12,
    ),
    Fixture(
        filename="13.png",
        label="Przykład 13",
        title="Zdjęcie telefonem — perspektywa i cień",
        layout="A",
        targets=["Piotr Wiśniewski"],
        distortion="keystone + obrót 1.4° + gradient światła + rozmycie",
        why=(
            "Rows are trapezoids, not rectangles: row height and column x-offsets "
            "both drift down the page. A rotation-only deskew cannot fix this. "
            "Also the realistic 'caseworker photographs the page' input, which "
            "the PRD's image-only MVP does not exclude."
        ),
        scenarios=[
            {
                "query": "Piotr Wiśniewski",
                "expected_matches": 1,
                "expected_rows": [3],
                "must": "band is a quadrilateral or the image is rectified first",
            },
        ],
        build=f13,
    ),
    Fixture(
        filename="14.png",
        label="Przykład 14",
        title="Wiersze o bardzo różnej wysokości",
        layout="A",
        targets=["Paulina Lewandowska"],
        distortion="lekkie pochylenie + szum",
        why=(
            "Breaks any fixed row-pitch assumption. Rows 2, 4 and 6 wrap to 3-4 "
            "lines while their neighbours are 2. Splitting the table by an "
            "averaged row height merges row 6 into row 7 — and row 7 is a "
            "different person who must stay redacted."
        ),
        scenarios=[
            {
                "query": "Paulina Lewandowska",
                "expected_matches": 1,
                "expected_rows": [6],
                "must": "row 6 is 4 text lines tall; row 7 must not be revealed by an over-tall band",
            },
        ],
        build=f14,
    ),
    Fixture(
        filename="15.png",
        label="Przykład 15",
        title="Gęsta tabela, 22 wiersze, mały odstęp",
        layout="B",
        targets=["Lidia Lisowska"],
        distortion="drobna fala + szum, czcionka 12pt",
        why=(
            "Row separation at the resolution limit: ~24px pitch with a 12pt "
            "font. A one-row-off error is invisible to a human skimming the "
            "output but exposes the wrong debtor. Also the throughput case — "
            "22 rows means 21 redaction bands, all of which must land."
        ),
        scenarios=[
            {
                "query": "Lidia Lisowska",
                "expected_matches": 1,
                "expected_rows": [12],
                "must": "exactly one of 22 rows visible; off-by-one row selection must be caught",
            },
        ],
        build=f15,
    ),
    Fixture(
        filename="16.png",
        label="Przykład 16",
        title="Tabela bez linii siatki",
        layout="C",
        targets=["Mariusz Kamiński"],
        distortion="obrót 1.7° + szum",
        why=(
            "Removes the crutch. Layout analysis that finds rows by detecting "
            "horizontal rules returns zero rows here; the structure exists only "
            "as whitespace gutters between text clusters. Tests whether row "
            "reconstruction is geometry-driven or line-driven."
        ),
        scenarios=[
            {
                "query": "Mariusz Kamiński",
                "expected_matches": 1,
                "expected_rows": [5],
                "must": "rows recovered from text clustering, not ruling lines",
            },
        ],
        build=f16,
    ),
    Fixture(
        filename="17.png",
        label="Przykład 17",
        title="Zagięcie kartki i cień na zgięciu",
        layout="A",
        targets=["Justyna Mazur"],
        distortion="lokalne wypiętrzenie na wysokości 52% + pas cienia",
        why=(
            "A discontinuity rather than a smooth warp: rows near the crease are "
            "compressed vertically and darkened. Binarisation with a global "
            "threshold turns the shadow band into ink and can swallow a row "
            "boundary entirely."
        ),
        scenarios=[
            {
                "query": "Justyna Mazur",
                "expected_matches": 1,
                "expected_rows": [8],
                "must": "the crease shadow near row 4-5 must not be read as a rule line or as content",
            },
        ],
        build=f17,
    ),
    Fixture(
        filename="18.png",
        label="Przykład 18",
        title="Tabela ucięta u dołu strony",
        layout="A",
        targets=["Jan Kowalski", "Piotr Wiśniewski"],
        distortion="obrót -1.1°, tabela wychodzi poza dolną krawędź",
        why=(
            "The vertical counterpart of `5.png`. 14 rows are laid out but the "
            "page ends mid-row: the last row has no bottom boundary. A band "
            "computed from content extent stops short of the page edge and "
            "leaves a strip of the truncated row visible. Also puts a target in "
            "row 1, flush under the header, where an over-reaching band eats the "
            "column titles."
        ),
        scenarios=[
            {
                "query": "Jan Kowalski",
                "expected_matches": 1,
                "expected_rows": [1],
                "must": "band above row 1 must not destroy the header; partial bottom row must still be fully redacted",
            },
        ],
        build=f18,
        notes=(
            "26 rows are laid out but the sheet ends inside row 23: rows 1-22 "
            "are complete, row 23 is clipped mid-text and has no closing rule, "
            "and rows 24-26 are off-page entirely. ground_truth_rows lists all "
            "26 as laid out — rows 23-26 are NOT recoverable from the image."
        ),
    ),
    Fixture(
        filename="19.png",
        label="Przykład 19",
        title="Tabela z jednym wierszem",
        layout="A",
        targets=["Katarzyna Wójcik"],
        distortion="obrót 0.7° + szum",
        why=(
            "Degenerate case: the match is the only row, so there is nothing to "
            "redact. Row-pitch inference from row-to-row deltas has no delta to "
            "work with. Output must still be a valid PDF with the row intact."
        ),
        scenarios=[
            {
                "query": "Katarzyna Wójcik",
                "expected_matches": 1,
                "expected_rows": [1],
                "must": "zero redaction bands, valid output, source untouched",
            },
        ],
        build=f19,
    ),
    Fixture(
        filename="20.png",
        label="Przykład 20",
        title="Tabela bez wierszy danych",
        layout="A",
        targets=[],
        distortion="szum",
        why=(
            "Header row only. `inspect` must report zero rows rather than "
            "mistaking the header for data, and `search` must return no match "
            "without crashing on an empty row set."
        ),
        scenarios=[
            {
                "query": "Jan Kowalski",
                "expected_matches": 0,
                "expected_rows": [],
                "must": "0 data rows reported; header not counted as a row",
            },
        ],
        build=f20,
    ),
    Fixture(
        filename="21.png",
        label="Przykład 21",
        title="Puste komórki i brakujące dane",
        layout="A",
        targets=["Mariusz Kamiński"],
        distortion="szum",
        why=(
            "Row 6 is entirely blank; row 2 has no address, row 3 no creditor, "
            "row 4 no given name and no amount. Row detection driven by 'where "
            "is there text' drops the blank row and shifts every row index below "
            "it — the classic off-by-one that redacts the wrong person."
        ),
        scenarios=[
            {
                "query": "Mariusz Kamiński",
                "expected_matches": 1,
                "expected_rows": [5],
                "must": "blank row 6 still counts as a row; empty cells must not collapse the row index",
            },
            {
                "query": "Wójcik",
                "expected_matches": 1,
                "expected_rows": [4],
                "must": "row 4 has no given name, so its full name is literally 'Wójcik' — decide and document whether a surname-only row is addressable by a surname-only query",
            },
        ],
        build=f21,
    ),
    Fixture(
        filename="22.png",
        label="Przykład 22",
        title="Pieczątka, dopisek odręczny i dziurkacz",
        layout="A",
        targets=["Paulina Lewandowska"],
        distortion="pieczątka 13°, odręczny dopisek, 3 dziurki, nierówne światło",
        why=(
            "Non-table ink crossing row boundaries. The stamp spans rows 2-4, "
            "the biro line crosses rows 2-4, and the punch holes sit in the left "
            "margin next to the Lp. column. OCR emits fragments for all of it; "
            "unfiltered, they distort row boundaries and produce phantom cells."
        ),
        scenarios=[
            {
                "query": "Paulina Lewandowska",
                "expected_matches": 1,
                "expected_rows": [6],
                "must": "stamp/handwriting fragments must not shift row boundaries; punch holes must not be read as content",
            },
        ],
        build=f22,
    ),
    Fixture(
        filename="23.png",
        label="Przykład 23",
        title="Dwie tabele na jednej stronie",
        layout="A",
        targets=["Mariusz Kamiński"],
        distortion="obrót -1.3° + szum",
        why=(
            "Two separate tables with the same column headers and both numbered "
            "from 1. A single global row index is ambiguous — 'row 1' names two "
            "different people. Tests whether row identity carries its table, and "
            "whether the second header row is excluded from the row set."
        ),
        scenarios=[
            {
                "query": "Mariusz Kamiński",
                "expected_matches": 1,
                "expected_rows": ["B1"],
                "must": "row identity is (table, index); the repeated header must not be counted as data",
            },
        ],
        build=f23,
        notes="Row numbering restarts at 1 in the second table. Manifest indices are prefixed A/B by table.",
    ),
    Fixture(
        filename="24.png",
        label="Przykład 24",
        title="Blada kserokopia, niski kontrast, artefakty JPEG",
        layout="B",
        targets=["Anna Nowak"],
        distortion="kontrast 0.55, JPEG q30, szum solny, szerokość 760 px",
        why=(
            "Risk #4 at its source. Rendered small, washed out and JPEG-crushed "
            "so that OCR confidence collapses while the rows stay readable to a "
            "human — deliberately marginal rather than illegible, so a wrong "
            "read is a defect and not an inevitability. The correct behaviour "
            "is loud flagging, not a confident wrong read: this is the fixture "
            "that should make FR-002 fire."
        ),
        scenarios=[
            {
                "query": "Anna Nowak",
                "expected_matches": 1,
                "expected_rows": [2],
                "must": "low-confidence fragments flagged (FR-002); a confident-but-wrong match here is the worst outcome",
            },
        ],
        build=f24,
    ),
]


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------

# `1.png`-`6.png` were produced by an image model and are not reproducible from
# this script. Their metadata is transcribed from
# `context/foundation/test-plan.md` section 2 "Fixture set"; row-level ground
# truth is deliberately null because it has never been hand-labelled.
ORIGINAL_SET: list[dict[str, Any]] = [
    {
        "filename": "1.png",
        "label": "Przykład 1",
        "title": "Skan czysty, ale lekko pochylony",
        "layout": "A",
        "distortion": "lekkie pochylenie",
    },
    {
        "filename": "2.png",
        "label": "Przykład 2",
        "title": "Cienie i nierówne oświetlenie",
        "layout": "B",
        "distortion": "cienie, nierówne światło",
    },
    {
        "filename": "3.png",
        "label": "Przykład 3",
        "title": "Pofalowanie strony",
        "layout": "A",
        "distortion": "łagodne pofalowanie",
    },
    {
        "filename": "4.png",
        "label": "Przykład 4",
        "title": "Niska jakość, rozmycie i szum",
        "layout": "B",
        "distortion": "rozmycie, szum",
    },
    {
        "filename": "5.png",
        "label": "Przykład 5",
        "title": "Kolumny ucięte przy prawej krawędzi",
        "layout": "C",
        "distortion": "ucięta prawa kolumna",
    },
    {
        "filename": "6.png",
        "label": "Przykład 6",
        "title": "Linie skanowania i artefakty",
        "layout": "B",
        "distortion": "linie skanowania, artefakty",
    },
]


def _rows_for_manifest(fixture: Fixture) -> list[dict[str, Any]]:
    """Rows as actually rendered. An empty list means "no data rows" (a real
    fact about the fixture), never "not labelled yet"."""
    return [
        {
            "index": p.lp or None,
            "imie": p.imie,
            "nazwisko": p.nazwisko,
            "full_name": p.full_name,
            "adres": [line for line in p.adres if line],
            "kwota": p.kwota,
            "wierzyciel": " ".join(w for w in p.wierzyciel if w),
        }
        for p in fixture.people
    ]


def build_manifest() -> dict[str, Any]:
    return {
        "$comment": (
            "Fixture identity comes from THIS file, not from the filename — "
            "see context/foundation/test-plan.md §2 finding 4. The in-page "
            "'Przykład N' title is the authoritative human label. Files 7+ are "
            "generated by generate_edge_cases.py and their rows are exact by "
            "construction; files 1-6 are image-model output with no ground truth."
        ),
        "generated_by": "context/test_images/generate_edge_cases.py",
        "page_size_px": [PAGE_W, PAGE_H],
        "layouts": {
            "A": "Lp. + rozdzielone imię/nazwisko, 6 kolumn",
            "B": "Lp. + scalone imię i nazwisko, 5 kolumn",
            "C": "bez Lp., rozdzielone imię/nazwisko, 5 kolumn",
        },
        "contains_real_pii": False,
        "fixtures": [
            {**entry, "generated": False, "ground_truth_rows": None}
            for entry in ORIGINAL_SET
        ]
        + [
            {
                "filename": f.filename,
                "size_px": list(f.size_px),
                "label": f.label,
                "title": f.title,
                "layout": f.layout,
                "distortion": f.distortion,
                "generated": True,
                "why_this_edge_case": f.why,
                "search_scenarios": f.scenarios,
                "notes": f.notes or None,
                "ground_truth_rows": _rows_for_manifest(f),
            }
            for f in FIXTURES
        ],
    }


# --------------------------------------------------------------------------


def verify() -> None:
    """Fail loudly if a declared scenario disagrees with the rendered rows.

    The scenarios are the reason this fixture set is worth anything, so a
    scenario that quietly stops matching its own image is worse than no
    scenario at all. Runs after every generation.
    """
    problems: list[str] = []
    for fixture in FIXTURES:
        names = [p.full_name for p in fixture.people if p.full_name]
        for name in set(names):
            count = names.count(name)
            expected = max(
                (
                    sc["expected_matches"]
                    for sc in fixture.scenarios
                    if sc["query"] == name
                ),
                default=None,
            )
            if count > 1 and expected != count:
                problems.append(
                    f"{fixture.filename}: {name!r} appears {count}x but no "
                    f"scenario declares it ambiguous"
                )
        for sc in fixture.scenarios:
            hits = [p.lp for p in fixture.people if p.full_name == sc["query"]]
            declared = [str(r) for r in sc["expected_rows"]]
            if hits != declared or len(hits) != sc["expected_matches"]:
                problems.append(
                    f"{fixture.filename}: query {sc['query']!r} declares "
                    f"{sc['expected_matches']}{declared}, image has "
                    f"{len(hits)}{hits}"
                )
    if problems:
        joined = "\n  ".join(problems)
        raise SystemExit(f"manifest/image mismatch:\n  {joined}")
    print("verify: every search scenario agrees with the rendered rows")


def main() -> None:
    for fixture in FIXTURES:
        img, rows = fixture.build()
        # Record what was actually rendered so the manifest cannot claim a row
        # the image does not contain.
        fixture.people = rows
        fixture.size_px = (img.width, img.height)
        path = OUT_DIR / fixture.filename
        img.convert("L").save(path, format="PNG", optimize=True)
        print(f"{fixture.filename:>8}  {img.width}x{img.height}  {fixture.title}")

    verify()

    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(build_manifest(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nwrote {manifest_path.name} ({len(FIXTURES)} generated fixtures)")


if __name__ == "__main__":
    main()
