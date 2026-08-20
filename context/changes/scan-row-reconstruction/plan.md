# Scan Row Reconstruction (S-01) Implementation Plan

## Overview

Implement roadmap slice S-01: `cover-data inspect <image>` runs local OCR on a scanned debtor-list page, reconstructs the logical table rows, and shows them in the terminal with low-confidence OCR fragments flagged and geometric ambiguity surfaced. This is the project's north-star slice — it proves the assumption everything else rests on, that row/table geometry can be resolved correctly as data even when the scan is distorted.

Covers PRD FR-001 (point at an image file on disk), FR-002 (OCR with per-fragment confidence, low-confidence flagged), FR-003 (reconstruct logical table rows tolerant of misalignment), US-01's first half, and the NFR on temporary artifacts.

## Current State Analysis

- `src/cover_data/cli.py:37` — `inspect` is a zero-argument `@app.command()` stub calling `_not_yet_implemented("S-01")`, which echoes and exits 1. No image-path argument exists; F-01 deliberately deferred its signature to this plan.
- `src/cover_data/__init__.py` — `main()` only calls `app()` and must stay zero-arg (the PyInstaller build in `.github/workflows/release.yml` depends on it).
- `pyproject.toml` — `requires-python = ">=3.14"`, one runtime dependency (`typer>=0.27.1`), `[tool.mypy] strict = true, files = ["src"]`, and a `slow` pytest marker already registered and described as "fixture-heavy OCR or full-page redaction test". `.python-version` is `3.14`; the venv is 3.14.7.
- No OCR, image, geometry, or PDF code or dependency exists anywhere in `src/`. This is a clean slate.
- `tests/test_cli.py` uses `typer.testing.CliRunner`, one test per behavior. There is no `tests/fixtures/` and no `conftest.py`.
- `lefthook.yml` gates commits on ruff format/check, `pytest -m 'not slow'`, and `mypy src`; pre-push and `.github/workflows/ci.yml` run the full suite including `slow`, plus `uv lock --check`.
- Six fixtures at `context/test_images/1.png`–`6.png` (the `7.png` gap was closed in `3f451c5`).
- `rich` is already importable — Typer bundles it. No new dependency is needed for formatted terminal output.

### Key Discoveries:

- **All six fixtures are fully-ruled bordered tables.** Every one has explicit horizontal *and* vertical ruling lines. `context/changes/scan-row-reconstruction/research.md` designed an anchor-seeded, strip-by-strip text-fragment growth pipeline without accounting for this — that is the design for a *borderless* table. Horizontal ruling lines yield row **extent** directly, which is the exact quantity `context/foundation/test-plan.md` Risks #1 and #2 turn on (row index is not row extent).
- **Every data row is multi-line.** The address cell wraps to two lines in nearly every row across all six fixtures, so clustering OCR text lines naively yields ~16 lines for 8 rows. Multi-line row grouping is mandatory, not an edge case; ruling lines handle it for free.
- **Two fixtures attack ruling-line detection specifically.** `6.png`'s "artifacts" are full-height *vertical* streaks that a naive vertical-line detector reads as column separators — horizontal detection is unaffected. `5.png`'s rightmost column runs off the page edge with no closing vertical line, and is the test-plan's sharpest test of Risks #1/#2.
- **The Paddle stack on 3.13 is verified, not assumed.** `uv pip compile` for `paddleocr[doc-parser]` + `paddlepaddle` at `--python-version 3.13 --python-platform windows` resolves to 97 packages including `paddlepaddle==3.3.1`, with `opencv-contrib-python`, `pypdfium2`, `pydantic`, `shapely`, `pyclipper`, `scipy`, and `pillow` arriving free and no `torch`.
- **The OCR engine decision is already locked** in `context/foundation/tech-stack.md` ("OCR engine and Python version"): PaddleOCR local, Python 3.13, develop-on-Paddle/ship-on-ONNX, engine behind a `Protocol`, weights pre-placed and never fetched at inference. That document explicitly states the pin, `.python-version`, CI, and `CLAUDE.md` are updated "as part of S-01". Not reopened here.
- **PP-Structure is excluded as a geometry source** by the same document — its table models self-report 59.5–69.7% on their own hard-table set and are trained on born-digital renders. Usable only as an optional disagreement signal.
- `context/foundation/test-plan.md` §3 Phase 1 lists change folder `context/changes/testing-fixture-foundation/` as "change opened". That folder does not exist on disk — the entry is stale, and the fixture-manifest work it describes lands in Phase 2 of this plan instead.

## Desired End State

`uv run cover-data inspect context/test_images/3.png` prints a formatted table of eight reconstructed debtor rows, each showing its cell text, its pixel row extent, a flag on any fragment below the confidence threshold, and a flag on any geometric ambiguity detected for that row. `--overlay out.png` additionally writes a copy of the scan with the detected row bands and column lines drawn over it, so the geometry can be checked by eye. The source image is byte-identical afterwards, and no file other than an explicitly-requested overlay exists on disk when the command returns — on the success path, the failure path, or an interrupt.

Verified by: the full gate (`ruff`, `mypy --strict`, `pytest` including `slow`) green on Python 3.13; row extents matching hand-labelled ground truth on `1.png`, `3.png`, and `5.png`; and a human confirming the overlay bands sit on the true row boundaries.

## What We're NOT Doing

- **No search, matching, confirmation prompt, or preview** — FR-004 through FR-007 are S-02 (`person-search-confirm`). This slice detects and *surfaces* ambiguity signals; it does not gate on them.
- **No redaction, no PDF output, no image writing beyond the optional overlay** — FR-008/FR-009 are S-03 (`selective-redaction-output`).
- **No PDF ingestion** — FR-001 scopes v1 to an image file already on disk; PDF is a named fast-follow (roadmap "Parked").
- **No PP-Structure / table-transformer / ML table-structure model** as a geometry source, per `tech-stack.md`.
- **No `img2table` or other third-party table-extraction library** — decided during planning; geometry is owned directly against OpenCV so per-fragment confidence retention and the coordinate contract stay under our control.
- **No ONNX export or PyInstaller work** — the develop-on-Paddle/ship-on-ONNX mitigation lands on `release.yml` and is out of scope until the pipeline is proven.
- **No testing of the OCR engine's own character accuracy** — `test-plan.md` §7 declares this deliberate negative space.
- **No hand-labelled ground truth for `2.png`, `4.png`, `6.png`** — those get structural assertions only in this slice.
- **No `--json` output surface** — deliberately declined so the domain model can still change shape before S-02 couples to it.

## Implementation Approach

Six phases, each independently committable and verifiable.

The Python 3.13 migration goes first and alone, so that it can be proven inert — gates green, no behavior change — before a 97-package dependency stack lands on top of it. A failure after a combined change would be ambiguous between the two causes.

Ground-truth labelling goes second, before any geometry code exists. This ordering is the point: `test-plan.md` Risk #1's named anti-pattern is an oracle lifted from the implementation, and the only structural defence is to write the oracle first.

The domain model and OCR adapter come third and establish the contract the remaining phases obey: every coordinate the model carries is in **original, unresampled source-image pixels**. Document unwarping is a read-side aid only — its transform is inverted before any geometry is recorded, with a round-trip assertion proving it. Getting this wrong is invisible until S-03 redacts the wrong pixels.

Geometry then derives row extents from horizontal ruling lines and a per-document column schema from vertical ruling lines, with OCR text-fragment clustering run as a genuinely independent second opinion. Ambiguity signals are computed from the disagreement between those two and from intrinsic geometric checks, stored on the typed row model for S-02 to consume. The CLI surface lands last, once there is something real to display.

## Critical Implementation Details

**Coordinate space is load-bearing and ordering-sensitive.** PaddleOCR's document-unwarping and orientation models resample pixels. Any geometry captured downstream of them is in *unwarped* space and will not address the right pixels in the source image. The inverse transform must be applied at the adapter boundary — before an `OcrFragment` is constructed — not deferred to a later consumer. Phase 3 asserts this by round-trip: a known point mapped forward then back must land within tolerance of itself.

**Vertical and horizontal line detection need different defences.** `6.png` carries full-height vertical scan streaks that pass every plausible "is this a long vertical line" test. Column detection must therefore corroborate candidate vertical lines against the header row's cell structure or against detected text-column gaps, rather than trusting line length alone. Row detection from horizontal lines has no equivalent adversary in this fixture set.

**`5.png`'s table has no right border.** A column schema derived purely from paired vertical lines will drop its last column, and a row band computed from detected *content* extent rather than *page* extent stops short of the page edge and would leave truncated text exposed in S-03. Row extents must extend to the page edge where no closing vertical line is found.

**The PaddleOCR result field names must be confirmed against the installed version.** The 3.x pipeline API (`PaddleOCR(...).predict()` returning `rec_texts` / `rec_scores` / polygon arrays, with `text_detection_model_dir`-style directory pinning) differs from the 2.x API (`.ocr()`, `det_model_dir`), and published documentation mixes the two. Confirm empirically at implementation time; the `Protocol` adapter is what confines this to one file.

## Phase 1: Python 3.13 migration and offline OCR stack

### Overview

Move the interpreter pin from 3.14 to 3.13, prove the move is inert, then add the PaddleOCR dependency stack and pre-place model weights so inference never touches the network.

### Changes Required:

#### 1. Interpreter pin

**File**: `.python-version`, `pyproject.toml`

**Intent**: Enact the version decision already recorded in `tech-stack.md`, which `paddlepaddle`'s `cp313`-capped wheels force.

**Contract**: `.python-version` becomes `3.13`; `pyproject.toml` `requires-python` becomes `>=3.13`. `.github/workflows/ci.yml` and `release.yml` need no edit — both deliberately omit a `python-version` input and read `.python-version` via `setup-uv`. Re-lock and re-run the full gate before adding anything else, to confirm the downgrade changes no behavior.

#### 2. OCR dependency stack

**File**: `pyproject.toml`, `uv.lock`

**Intent**: Add the local OCR engine and its geometry toolchain.

**Contract**: `uv add --system-certs "paddleocr[doc-parser]" paddlepaddle` — `--system-certs` is mandatory on this network's TLS-inspecting proxy. Expect ~97 resolved packages; `opencv-contrib-python`, `numpy`, `pillow`, `shapely`, `pyclipper`, `scipy`, `pydantic`, and `pypdfium2` arrive transitively and need no explicit add. Do not add `torch` or `img2table`.

#### 3. Model weights, pinned and offline

**File**: `models/` (new, git-ignored), `src/cover_data/ocr/config.py` (new)

**Intent**: Pre-place the detection, recognition, unwarping, and orientation weights and pin their directories explicitly, so the tool never attempts network I/O at inference — required both by the PII-stays-on-device invariant and because the proxy breaks first-run downloads.

**Contract**: A module-level constant resolving the model root, plus per-model directory paths passed explicitly at engine construction. `models/` is git-ignored and its provisioning documented in `CLAUDE.md`. Polish is selected via `lang="pl"`.

#### 4. Stack documentation

**File**: `CLAUDE.md`

**Intent**: `CLAUDE.md` still states Python 3.14 and lists `typer` as the only runtime dependency. Update the stack and commands sections, and document how `models/` is provisioned.

**Contract**: Prose only. `context/foundation/tech-stack.md` already records this decision and needs no edit.

### Success Criteria:

#### Automated Verification:

- `uv lock --check` passes and `uv sync --locked` succeeds on 3.13
- Full gate green after the pin move, before dependencies are added: `uv run ruff check . && uv run mypy src && uv run pytest`
- Full gate green again after the dependency stack lands
- `uv run python -c "import paddleocr, cv2"` succeeds

#### Manual Verification:

- A one-off script OCRs `context/test_images/1.png` and prints recognized Polish text with per-fragment scores, with the machine's network disabled or the model directories confirmed as the only source

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Fixture manifest and row-extent ground truth

### Overview

Establish fixture identity from an explicit manifest rather than filenames, and hand-label row-extent ground truth for the three highest-value fixtures — written before any geometry code exists, so the oracle cannot be derived from the code it will judge.

### Changes Required:

#### 1. Fixture manifest

**File**: `tests/fixtures/manifest.toml` (new)

**Intent**: Give each fixture a stable identity, its distortion category, and its column variant. `test-plan.md` §2 finding 4 records that filename-derived identity was already wrong once here (`7.png` labelled "Przykład 6"), so the in-page title is authoritative, not the filename.

**Contract**: One entry per fixture keyed by a stable id, carrying: source path under `context/test_images/`, in-page label, distortion category, column-variant tag (A/B/C), expected data-row count (8 for all six), and whether row-extent ground truth exists.

#### 2. Row-extent ground truth

**File**: `tests/fixtures/ground_truth/*.toml` (new)

**Intent**: Hand-labelled top and bottom pixel boundaries for each of the eight data rows in `1.png` (clean baseline), `3.png` (waviness), and `5.png` (cut-off columns) — roughly 24 bands.

**Contract**: Per fixture, an ordered list of row bands with `top` and `bottom` in original source-image pixel coordinates, plus the header row's band. Labelled by eye from the image — never produced by running the code under test. Record the labelling method in the file so a later reader can tell it was independent.

#### 3. Fixture loading helpers

**File**: `tests/conftest.py` (new)

**Intent**: Give tests typed access to the manifest and ground truth without re-parsing TOML at each call site.

**Contract**: Pytest fixtures exposing the manifest entries and, for labelled fixtures, their row bands. A parametrized fixture over "all fixtures" and over "labelled fixtures only" so later phases can assert structurally on all six and dimensionally on the labelled three.

### Success Criteria:

#### Automated Verification:

- `uv run pytest tests/test_fixtures.py` passes: manifest parses, every referenced image exists, every fixture declares 8 data rows
- Ground-truth bands are internally consistent — monotonically increasing, non-overlapping, 8 data bands per labelled fixture
- `uv run mypy src` still passes (no `src/` change, but the gate must stay green)

#### Manual Verification:

- Ground-truth bands, when drawn over their source images, visibly sit on the true row boundaries for all three labelled fixtures

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Typed domain model and OCR adapter

### Overview

Define the typed OCR-fragment model and the swappable engine `Protocol`, implement the PaddleOCR adapter, and establish the coordinate contract that Phases 4–6 and both downstream slices depend on.

### Changes Required:

#### 1. Domain model

**File**: `src/cover_data/domain.py` (new)

**Intent**: The typed structures `CLAUDE.md` mandates in place of dicts — this is a domain invariant, because an untyped dict makes a fragment → cell → row shape mismatch invisible until runtime.

**Contract**: `OcrFragment` carrying recognized text, a four-point polygon in original source-image pixels, an axis-aligned bounding box derived from it, the engine's confidence score, and a `low_confidence` flag. Frozen and immutable. Confidence is retained on every fragment regardless of the flag — flagging never filters, so a sub-threshold fragment still reaches the row model and the display.

#### 2. Engine protocol and adapter

**File**: `src/cover_data/ocr/engine.py`, `src/cover_data/ocr/paddle.py` (new)

**Intent**: Keep Paddle, a future ONNX runtime, and Tesseract swappable behind one interface, as `tech-stack.md` requires — this is what makes the develop-on-Paddle/ship-on-ONNX plan not a one-way door.

**Contract**: A `Protocol` with a single method taking an image path and returning a sequence of `OcrFragment`. The Paddle adapter constructs the pipeline once with explicitly pinned model directories and `lang="pl"`, and is the only module in the codebase that imports `paddleocr` or knows its result field names. Confirm those field names against the installed version — published docs mix the 3.x `predict()`/`rec_texts`/`rec_scores` API with the 2.x `.ocr()`/`det_model_dir` API.

#### 3. Coordinate contract

**File**: `src/cover_data/ocr/paddle.py`, `src/cover_data/geometry/transform.py` (new)

**Intent**: Every coordinate leaving the adapter is in original, unresampled source pixels. Document unwarping and orientation correction improve what OCR reads; they must never define the space geometry is recorded in, or S-03 will overwrite the wrong pixels.

**Contract**: The transform applied by any preprocessing step is captured and inverted before fragments are constructed. Expose the forward and inverse mapping as a small explicit type rather than leaving it implicit inside the adapter, so the round-trip is testable in isolation.

#### 4. Confidence threshold

**File**: `src/cover_data/ocr/engine.py`

**Intent**: Implement FR-002's flagging with a documented default that a caller can override.

**Contract**: A named default constant with its rationale recorded in a comment, overridden per-run by the value the CLI passes down in Phase 6. Tests drive flagging behavior by supplying threshold values as *input* rather than asserting against the constant — `test-plan.md` Risk #4 names the latter as an anti-pattern.

### Success Criteria:

#### Automated Verification:

- Unit tests construct synthetic fragments at chosen confidence levels and assert the flag is set correctly at, above, and below threshold, and that no fragment is ever dropped
- Round-trip test: a known point mapped through the preprocessing transform and back lands within tolerance of itself
- A `slow`-marked test runs the real adapter over `1.png` and asserts fragments are returned with non-empty text, four-point polygons within image bounds, and confidences in the engine's documented range
- `uv run mypy src` passes under `strict = true`
- `uv run pytest -m 'not slow'` stays fast enough for the commit gate

#### Manual Verification:

- Recognized Polish text on `1.png` and `4.png` is inspected by eye for diacritic handling (ą/ć/ę/ł/ń/ó/ś/ź/ż) — this informs whether FR-005's exact-match assumption survives into S-02

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 4: Ruling-line row and column geometry

### Overview

Derive row extents from horizontal ruling lines and a per-document column schema from vertical ruling lines, assign fragments to cells, and run OCR text-fragment clustering as an independent second opinion.

### Changes Required:

#### 1. Ruling-line extraction

**File**: `src/cover_data/geometry/lines.py` (new)

**Intent**: Find the table's horizontal and vertical rules — the primary geometry signal, available because every supported document is a bordered debtor table.

**Contract**: Separate horizontal and vertical extraction using morphological opening with long thin structuring elements, returning line segments in original pixel coordinates. Horizontal extraction is the row-extent oracle. Vertical extraction must corroborate candidates against the header row's cell structure or text-column gaps rather than trusting line length alone — `6.png`'s full-height scan streaks otherwise register as column separators.

#### 2. Row bands

**File**: `src/cover_data/geometry/rows.py` (new)

**Intent**: Turn consecutive horizontal rules into row extents, and separate the header row from data rows.

**Contract**: A `RowBand` type carrying top and bottom in original pixels plus an index. Consecutive rule pairs become bands; bands narrower than a page-relative minimum are merged or discarded as artifacts. Where curvature makes a rule non-horizontal, the band boundary follows the rule rather than a single y-value, so the extent stays correct across the page width on `3.png`.

#### 3. Column schema, per document

**File**: `src/cover_data/geometry/columns.py` (new)

**Intent**: Derive the column layout from each document rather than hardcoding one, so all three fixture variants stay in scope — the resolution of PRD Open Question #2 settled during planning.

**Contract**: A `ColumnBand` sequence with left and right bounds and the header text recognized within each. Where no closing vertical rule is found before the page edge, the final column extends to the page edge rather than to detected content extent — `5.png`'s truncated right column depends on this, and getting it wrong is precisely the Risk #1 failure. The header row's recognized text names the columns; a merged `Imię i nazwisko` versus split `Imię` / `Nazwisko` is a recorded property of the document, not an error.

#### 4. Cell assignment and row assembly

**File**: `src/cover_data/geometry/table.py` (new), `src/cover_data/domain.py`

**Intent**: Place each `OcrFragment` into the cell whose row band and column band contain it, and assemble cells into rows.

**Contract**: `Cell` (column index, row index, the fragments it contains, joined text) and `TableRow` (index, `RowBand`, ordered cells) added to the domain model. A cell holds multiple fragments — the two-line address is the normal case across every fixture, so cell text joins its fragments in reading order rather than assuming one fragment per cell. A fragment falling outside every band is retained as unassigned, not dropped, and becomes an ambiguity signal in Phase 5.

#### 5. Independent text-cluster cross-check

**File**: `src/cover_data/geometry/cluster.py` (new)

**Intent**: Produce a second, genuinely independent row hypothesis from fragment positions alone, so its disagreement with the ruling-line result is a nearly-free correctness signal.

**Contract**: Cluster fragments into rows by vertical position using the anchor-column approach from the research — seed on the narrow, single-line name column where curvature is negligible, then group by proximity. Returns a row count and per-row fragment membership only; it must not consume the ruling-line output, or the independence that makes it valuable is lost.

### Success Criteria:

#### Automated Verification:

- `slow`-marked tests assert reconstructed row extents against Phase 2's hand-labelled ground truth for `1.png`, `3.png`, and `5.png`, within a stated pixel tolerance, on **both** the top and bottom edge of every band
- Structural assertions on all six fixtures: exactly 8 data rows plus 1 header row detected
- `5.png` specifically: the last column's right bound reaches the page edge, not the last detected content
- `6.png` specifically: the detected column count matches its variant-B schema, proving vertical streaks were rejected
- Every fragment is either assigned to a cell or explicitly retained as unassigned — none silently dropped
- `uv run mypy src` passes; `uv run pytest` fully green

#### Manual Verification:

- Row bands and column bands drawn over all six fixtures are inspected by eye and sit on the true boundaries, particularly on `3.png` where curvature is real

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 5: Ambiguity signals

### Overview

Compute the geometric and cross-check ambiguity signals the research identified, and store them on the typed row model. S-01 detects and surfaces; S-02 gates on them via FR-006.

### Changes Required:

#### 1. Signal types

**File**: `src/cover_data/domain.py`

**Intent**: Make ambiguity a first-class, typed property of a row rather than a log line, so S-02 can consume it without re-deriving geometry.

**Contract**: An enumerated signal kind plus a per-row collection of detected signals carrying the kind and a short human-readable detail. `TableRow` gains this collection. A row with no signals carries an empty collection, never `None`.

#### 2. Detectors

**File**: `src/cover_data/geometry/ambiguity.py` (new)

**Intent**: Implement the checks the research recommends hard-gating on, as pure functions over the assembled table.

**Contract**: Detectors for — cell count differing from the document's own detected column count; row-band boundaries crossing or non-monotone across the page width; row height beyond N·MAD of the page median; the text-cluster row count disagreeing with the ruling-line row count, or per-row membership disagreeing; any low-confidence fragment inside a row; and any unassigned fragment falling within a row's vertical extent. Each is independent and reports rather than corrects — none of them mutates the geometry.

### Success Criteria:

#### Automated Verification:

- Unit tests over synthetic tables trigger each detector in isolation and confirm it stays silent on a clean table
- No detector mutates the table it inspects
- Running the full pipeline over the clean baseline `1.png` produces zero or few signals; running it over `4.png` (blur) produces low-confidence signals — asserted as a relative comparison, not against an absolute count
- `uv run mypy src` passes; `uv run pytest` fully green

#### Manual Verification:

- Signals reported across all six fixtures are reviewed for plausibility — noise on every row would mean thresholds need tuning before S-02 can gate on them

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 6: `inspect` CLI surface

### Overview

Replace the stub with the real command: image argument, confidence override, optional geometry overlay, and a formatted terminal table — with no temporary artifacts and a verified-immutable source file.

### Changes Required:

#### 1. Command signature

**File**: `src/cover_data/cli.py`

**Intent**: Give `inspect` its real parameters, following the `Annotated[...]` convention F-01 established and `CLAUDE.md` mandates.

**Contract**: `inspect` takes an `Annotated[Path, typer.Argument(...)]` image path that must exist and be readable, an `Annotated[float, typer.Option("--min-confidence")]` defaulting to the Phase 3 constant, and an `Annotated[Path | None, typer.Option("--overlay")]` defaulting to `None`. Remove the `_not_yet_implemented("S-01")` call; leave the `search` and `redact` stubs untouched. Command logic stays out of `__init__.py`, whose `main()` remains zero-arg.

#### 2. Terminal rendering

**File**: `src/cover_data/render.py` (new)

**Intent**: Show reconstructed rows with confidence and ambiguity visible, using `rich` — already available via Typer, no new dependency.

**Contract**: One display row per reconstructed table row, showing row index, each cell's text, the row's pixel extent, and markers for low-confidence fragments and ambiguity signals. Sub-threshold text is visually distinguished in place rather than relegated to a footnote — `test-plan.md` Risk #4 is explicit that retaining the number is not flagging it. Rendering is a pure function of the table model so it is testable without invoking OCR.

#### 3. Geometry overlay

**File**: `src/cover_data/render.py`

**Intent**: Let the geometry be checked by eye — the fastest feedback loop for the one thing this slice exists to prove.

**Contract**: Given the source image and the assembled table, draw row-band boundaries and column-band boundaries over a copy and write it to the requested path. Written **only** when `--overlay` is passed; never to a default or temporary location.

#### 4. Artifact lifecycle and source immutability

**File**: `src/cover_data/pipeline.py` (new)

**Intent**: Satisfy the NFR and `test-plan.md` Risk #3 structurally rather than by cleanup, and defend Risk #7 while it is nearly free.

**Contract**: The pipeline holds every intermediate — preprocessed image, masks, line images — in memory; nothing is written to disk except an explicitly-requested overlay. Confirm empirically that the Paddle pipeline does not write scratch files of its own accord under this configuration; if it does, redirect it and assert the redirect is empty after a run. The source image is opened read-only and never passed to an in-place operation.

### Success Criteria:

#### Automated Verification:

- `CliRunner` tests: `inspect <fixture>` exits 0 and prints eight data rows; a missing path exits non-zero with a clear message; `--overlay <path>` writes that file and nothing else
- Without `--overlay`, no file is created anywhere under the working directory or the system temp directory during a run
- Source-immutability test: the fixture's SHA-256 and mtime are unchanged after a successful run, after a run that raises mid-pipeline, and after an interrupt
- `--min-confidence 1.0` marks every fragment low-confidence and `--min-confidence 0.0` marks none — flagging driven by input, not by asserting the constant
- Existing `tests/test_cli.py` still passes for `search` and `redact`; the `inspect` stub test is replaced, not deleted
- Full gate green: `uv run ruff format --check . && uv run ruff check . && uv lock --check && uv run pytest && uv run mypy src`

#### Manual Verification:

- `uv run cover-data inspect context/test_images/3.png --overlay out.png` — terminal table is readable and the overlay's bands sit on the true row boundaries
- The same on `5.png`, confirming the truncated right column is bounded at the page edge
- `uv run cover-data inspect --help` reads correctly for a first-time user
- Working tree is clean of stray artifacts after a full manual session

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful.

---

## Testing Strategy

### Unit Tests:

- Confidence flagging over synthetic fragments at, above, and below threshold; flag never filters
- Coordinate round-trip through the preprocessing transform
- Each ambiguity detector in isolation, on a synthetic table it should fire on and one it should not
- Cell assembly with multiple fragments per cell (the two-line address case)
- Terminal rendering as a pure function of a synthetic table model, no OCR involved

### Integration Tests:

- `slow`-marked: full pipeline over `1.png`, `3.png`, `5.png` asserting row extents against hand-labelled ground truth on both band edges simultaneously — never separately, since `test-plan.md` Risk #2 warns that separately-satisfiable assertions let the fix for one silently break the other
- Structural pass over all six fixtures: 8 data rows plus header
- `5.png`: final column bounded at page edge; `6.png`: vertical streaks rejected from the column schema
- CLI-level: exit codes, output shape, overlay written only on request, no stray files

### Manual Testing Steps:

1. Run `inspect` on each of the six fixtures with `--overlay` and confirm bands sit on true row boundaries
2. Inspect recognized Polish text for diacritic correctness on `1.png` and `4.png`
3. Confirm ambiguity signals are plausible rather than firing on every row
4. Confirm the working tree carries no stray artifacts after a session
5. Confirm the source fixtures are unmodified (`git status` clean)

## Performance Considerations

No latency budget applies — this is a single-user CLI run interactively on one page at a time, and a few seconds of OCR is acceptable. The one real constraint is the commit gate: `lefthook.yml` runs `pytest -m 'not slow'`, so every test that loads a fixture through the OCR engine must carry `@pytest.mark.slow`. The marker is already registered in `pyproject.toml` for exactly this purpose. Keep the Paddle pipeline construction at module or fixture scope rather than per-test — model loading, not inference, dominates.

## Migration Notes

The Python 3.14 → 3.13 move requires contributors to have 3.13 available; `uv` will fetch it. After pulling Phase 1, `.venv/` must be recreated — `uv sync --locked` handles this, but a stale 3.14 venv will produce confusing failures. `models/` is git-ignored and must be provisioned locally before any OCR test runs; document the provisioning step in `CLAUDE.md` so a fresh clone has a path forward. CI is unaffected by the version move itself, since both workflows read `.python-version` rather than pinning inline.

## References

- Research: `context/changes/scan-row-reconstruction/research.md`
- Contract: `context/foundation/prd.md` — FR-001, FR-002, FR-003, US-01, NFR; Open Question #2 resolved during this planning session
- Slice definition: `context/foundation/roadmap.md` — S-01
- Locked stack decision: `context/foundation/tech-stack.md` — "OCR engine and Python version"
- Risk map and anti-patterns: `context/foundation/test-plan.md` — Risks #1–#5, #7; §3 Phases 1–3; §7 negative space
- Prior slice conventions: `context/changes/cli-entrypoint-scaffold/plan.md`
- Attachment point: `src/cover_data/cli.py:37`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Python 3.13 migration and offline OCR stack

#### Automated

- [ ] 1.1 `uv lock --check` passes and `uv sync --locked` succeeds on 3.13
- [ ] 1.2 Full gate green after the pin move, before dependencies are added
- [ ] 1.3 Full gate green again after the dependency stack lands
- [ ] 1.4 `uv run python -c "import paddleocr, cv2"` succeeds

#### Manual

- [ ] 1.5 Offline OCR of `1.png` prints Polish text with per-fragment scores

### Phase 2: Fixture manifest and row-extent ground truth

#### Automated

- [ ] 2.1 Manifest parses; every referenced image exists; every fixture declares 8 data rows
- [ ] 2.2 Ground-truth bands are monotonic, non-overlapping, 8 data bands per labelled fixture
- [ ] 2.3 `uv run mypy src` still passes

#### Manual

- [ ] 2.4 Ground-truth bands drawn over their images sit on the true row boundaries

### Phase 3: Typed domain model and OCR adapter

#### Automated

- [ ] 3.1 Confidence flagging unit tests at, above, and below threshold; no fragment dropped
- [ ] 3.2 Coordinate round-trip test lands within tolerance
- [ ] 3.3 `slow`-marked adapter test over `1.png` returns in-bounds polygons and valid confidences
- [ ] 3.4 `uv run mypy src` passes under `strict = true`
- [ ] 3.5 `uv run pytest -m 'not slow'` stays fast enough for the commit gate

#### Manual

- [ ] 3.6 Polish diacritic handling inspected on `1.png` and `4.png`

### Phase 4: Ruling-line row and column geometry

#### Automated

- [ ] 4.1 Row extents match ground truth on `1.png`, `3.png`, `5.png` — both band edges asserted together
- [ ] 4.2 All six fixtures detect exactly 8 data rows plus 1 header row
- [ ] 4.3 `5.png`'s last column right bound reaches the page edge
- [ ] 4.4 `6.png`'s column count matches variant B — vertical streaks rejected
- [ ] 4.5 Every fragment is assigned or explicitly retained as unassigned; none dropped
- [ ] 4.6 `uv run mypy src` passes; `uv run pytest` fully green

#### Manual

- [ ] 4.7 Row and column bands drawn over all six fixtures sit on true boundaries, especially `3.png`

### Phase 5: Ambiguity signals

#### Automated

- [ ] 5.1 Each detector fires in isolation and stays silent on a clean table
- [ ] 5.2 No detector mutates the table it inspects
- [ ] 5.3 `4.png` produces more low-confidence signals than `1.png` (relative assertion)
- [ ] 5.4 `uv run mypy src` passes; `uv run pytest` fully green

#### Manual

- [ ] 5.5 Signals across all six fixtures reviewed for plausibility, not blanket noise

### Phase 6: `inspect` CLI surface

#### Automated

- [ ] 6.1 `inspect <fixture>` exits 0 and prints eight data rows; missing path exits non-zero
- [ ] 6.2 `--overlay <path>` writes that file and nothing else
- [ ] 6.3 Without `--overlay`, no file is created in the working directory or system temp
- [ ] 6.4 Source SHA-256 and mtime unchanged after success, mid-pipeline failure, and interrupt
- [ ] 6.5 `--min-confidence 1.0` flags all fragments, `0.0` flags none
- [ ] 6.6 `search`/`redact` stub tests still pass; `inspect` stub test replaced
- [ ] 6.7 Full gate green: format-check, lint, lockfile, pytest, mypy

#### Manual

- [ ] 6.8 `inspect 3.png --overlay out.png` — table readable, bands on true boundaries
- [ ] 6.9 `inspect 5.png` — truncated right column bounded at page edge
- [ ] 6.10 `inspect --help` reads correctly for a first-time user
- [ ] 6.11 Working tree clean of stray artifacts after a manual session
