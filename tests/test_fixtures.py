"""Tests for `context/test_images/generate_edge_cases.py`'s fixture geometry
export (Phase 3 of `scan-row-reconstruction`).

`render_page` already computes exact row/column edges, but every fixture then
warps the rendered page (rotate, wave, fold, perspective, crop, downsample)
before it is saved. The generator threads a same-size label mask through the
*geometric* subset of that chain (`GeometryRecorder`) so the edges exported to
`manifest.json` describe where the rules actually land in the final PNG, in
final-image pixel coordinates -- see plan.md Phase 3 for the full contract.

These tests drive that mask/replay mechanism directly; they are deliberately
a small, focused set (per `test-plan.md`'s guidance against exhaustive
per-fixture unit tests) and are followed by the broader manifest-driven
structural checks the regenerated fixture set must satisfy.
"""

from __future__ import annotations

import generate_edge_cases as gen
import numpy as np
import pytest
from conftest import FixtureEntry
from PIL import Image, ImageDraw


def test_geometry_mask_round_trips_through_noop_geometric_chain() -> None:
    """3.2: a mask pushed through a chain of no-op geometric transforms
    (0-degree rotate, identity crop, identity-size resize) recovers its
    edges exactly. This is the mask contract's own regression guard -- if a
    "neutral" resample still perturbs a label, every exported boundary is
    silently biased."""
    with gen._recording() as rec:
        img = gen.render_page("Test", [gen.layout_a(gen.BASE[:2])])
        h, w = img.height, img.width
        img = gen.rotate(img, 0.0)
        img = gen.wave(img, amp=0.0, period=100.0)
        box = (0, 0, w, h)
        img = img.crop(box)
        gen._ACTIVE_RECORDER.log("crop", box=box)
        img = img.resize((w, h), Image.Resampling.LANCZOS)
        gen._ACTIVE_RECORDER.log("resize", w=w, h=h)

    assert rec.initial_row_mask is not None
    before = np.asarray(rec.initial_row_mask)
    after = np.asarray(rec.replay_mask(rec.initial_row_mask))
    assert np.array_equal(before, after)


def test_rotate_mask_uses_nearest_resampling_not_bicubic() -> None:
    """The mask contract requires NEAREST + zero-fill for every geometric
    transform (never `rotate`'s real BICUBIC/PAPER). A blending resample
    would invent intermediate label values between an edge's id and the
    background; NEAREST must not."""
    mask = Image.new("L", (60, 60), 0)
    ImageDraw.Draw(mask).line([(5, 30), (54, 30)], fill=7, width=2)

    with gen._recording() as rec:
        gen._ACTIVE_RECORDER.log("rotate", deg=5.0)
    rotated = rec.replay_mask(mask)

    values = set(np.unique(np.asarray(rotated)).tolist())
    assert values <= {0, 7}


def test_fit_page_mask_crop_inherits_image_derived_box() -> None:
    """3's mask contract: the mask inherits the page image's crop box rather
    than recomputing one from its own (much sparser) ink. Build an image
    whose real content ends around y=100 and a mask whose only labeled line
    sits at y=150 -- if the crop were (wrongly) recomputed from the mask, the
    mask's own ink at y=150 would push the box past the image-derived one."""
    img = Image.new("L", (50, 200), gen.PAPER)
    ImageDraw.Draw(img).rectangle([5, 5, 45, 100], fill=gen.INK)
    mask = Image.new("L", (50, 200), 0)
    ImageDraw.Draw(mask).line([(0, 150), (49, 150)], fill=3, width=1)

    with gen._recording() as rec:
        cropped_img = gen.fit_page(img, margin=10)
    cropped_mask = rec.replay_mask(mask)

    expected_box = gen._fit_page_crop_box(img, margin=10)
    assert cropped_img.size == cropped_mask.size
    assert cropped_mask.height == expected_box[3] - expected_box[1]
    assert cropped_mask.height < 150


def test_edge_polyline_recovery_flags_missing_label_as_clipped() -> None:
    """A row/column edge that warped entirely off the final image must be
    reported as clipped rather than silently dropped or clamped -- 18.png's
    bottom-truncated last row depends on this being distinguishable from an
    edge that legitimately sits at y=0."""
    mask = Image.new("L", (40, 40), 0)
    ImageDraw.Draw(mask).line([(0, 10), (39, 10)], fill=1, width=1)

    present = gen._edge_polyline(mask, 1, axis="row")
    missing = gen._edge_polyline(mask, 2, axis="row")

    assert present is not None
    assert present.points and not present.clipped
    assert missing is not None
    assert not missing.points
    assert missing.clipped


def test_perspective_mask_mapping_is_content_independent() -> None:
    """13.png's keystone warp is applied to both the real image and, via
    `_apply_geom_op`, to a mask/companion carrying no photographic content at
    all. That reuse is only valid if the perspective mapping depends solely
    on image size and the target quad, never on pixel content -- confirmed
    here by warping the same labeled point on two differently-textured
    backgrounds and requiring it lands in the same place both times, per the
    plan's explicit caveat about this being unverified."""
    quad = [(0.05, 0.03), (0.97, 0.01), (0.99, 0.97), (0.01, 0.99)]
    rng = np.random.default_rng(0)
    label_point = (20, 20)

    plain = Image.new("L", (40, 40), 0)
    ImageDraw.Draw(plain).point(label_point, fill=9)
    op = gen._GeomOp("perspective", {"quad": quad})
    warped_plain = np.asarray(gen._apply_geom_op(plain, op, mode="mask"))

    # Values kept away from the label (9) so warped background noise can
    # never coincidentally match it and mask a real mapping difference.
    textured = Image.fromarray(rng.integers(50, 255, (40, 40), dtype=np.uint8))
    ImageDraw.Draw(textured).point(label_point, fill=9)
    warped_textured = np.asarray(gen._apply_geom_op(textured, op, mode="mask"))

    assert (
        np.argwhere(warped_plain == 9).tolist()
        == np.argwhere(warped_textured == 9).tolist()
    )


# --------------------------------------------------------------------------
# Manifest-driven structural checks over the regenerated fixture set
# --------------------------------------------------------------------------


def test_every_manifest_fixture_image_exists_on_disk(any_fixture: FixtureEntry) -> None:
    assert any_fixture.path.is_file(), any_fixture.filename


def test_manifest_declares_geometry_for_generated_fixtures_only(
    fixture_entries: list[FixtureEntry],
) -> None:
    for entry in fixture_entries:
        if entry.generated:
            assert entry.geometry is not None, entry.filename
        else:
            assert entry.geometry is None, entry.filename


def test_geometry_row_and_column_edges_are_ordered_and_non_crossing(
    generated_fixture: FixtureEntry,
) -> None:
    assert generated_fixture.geometry is not None
    for table in generated_fixture.geometry["tables"]:
        row_ys = [edge["points"][0][1] for edge in table["row_edges"] if edge["points"]]
        assert row_ys == sorted(row_ys), generated_fixture.filename
        col_xs = [edge["points"][0][0] for edge in table["col_edges"] if edge["points"]]
        assert col_xs == sorted(col_xs), generated_fixture.filename


def test_geometry_row_edge_count_matches_ground_truth_row_count(
    generated_fixture: FixtureEntry,
) -> None:
    entry = generated_fixture
    assert entry.geometry is not None
    assert entry.ground_truth_rows is not None
    # row_edges = [header_top, header_bottom, row1_bottom, ..., rowN_bottom],
    # so its length is row count + 2, not + 1 (header contributes both ends).
    tables = entry.geometry["tables"]
    if entry.filename == "23.png":
        assert len(tables) == 2
        assert len(tables[0]["row_edges"]) - 2 == 4
        assert len(tables[1]["row_edges"]) - 2 == 4
    else:
        assert len(tables) == 1
        assert len(tables[0]["row_edges"]) - 2 == len(entry.ground_truth_rows)


@pytest.mark.parametrize(
    ("filename", "expected_rows"),
    [("20.png", 0), ("19.png", 1), ("26.png", 3), ("15.png", 22), ("18.png", 26)],
)
def test_degenerate_row_counts_match_manifest(
    fixture_entries: list[FixtureEntry], filename: str, expected_rows: int
) -> None:
    entry = next(e for e in fixture_entries if e.filename == filename)
    assert entry.ground_truth_rows is not None
    assert len(entry.ground_truth_rows) == expected_rows
