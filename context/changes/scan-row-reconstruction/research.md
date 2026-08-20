---
date: 2026-08-20T14:07:02+02:00
researcher: Lukasz Stefaniszyn
git_commit: fefff84d74ef8555a0fc4933e362a2f7e393c523
branch: main
repository: cover-data
topic: "Local OCR + row-reconstruction approach for a scanned debtor-list table (S-01)"
tags: [research, codebase, ocr, row-reconstruction, table-structure, python-3.14, rapidocr]
status: complete
last_updated: 2026-08-20
last_updated_by: Lukasz Stefaniszyn
last_updated_note: "Follow-up: re-opened the OCR engine decision with the Python 3.14 pin treated as negotiable; corrected the 'PaddleOCR is blocked' finding and switched the recommendation to Python 3.13 + native PaddleOCR"
---

# Research: Local OCR + row-reconstruction approach for a scanned debtor-list table (S-01)

**Date**: 2026-08-20T14:07:02+02:00
**Researcher**: Lukasz Stefaniszyn
**Git Commit**: fefff84d74ef8555a0fc4933e362a2f7e393c523
**Branch**: main
**Repository**: cover-data

## Research Question

For roadmap slice S-01 (change-id `scan-row-reconstruction`) — "user points the tool at a scanned debtor-list image and sees reconstructed table rows, with OCR confidence flagged on low-confidence fragments" — what is the proper technical solution? Specifically: which local (offline) OCR engine to use, and what algorithm reconstructs logical table rows from OCR fragments when the scan is skewed or wavy rather than a clean grid. Researched via Exa web search and Context7 library docs, grounded against the current codebase state and `context/README.md`'s high-level pipeline vision.

## Summary

**A real, deliberately-varied set of distorted sample scans exists** at `context/test_images/` (`1.png`–`5.png`, `7.png` — six files, gap at `6.png`), discovered mid-research. Each is labeled "Przykład N" (Example N) and demonstrates one distortion category: slight tilt, shadows/uneven lighting, wavy/curved paper, low-quality blur+noise, partially cut-off columns, and scan-line artifacts. These are **synthetic mockups** (clean printed Polish text, computer-generated table, not a photographed real-world debtor list) but they directly target the roadmap's blocking Open Question ("do we have a real representative distorted scan to build and validate row-reconstruction against?"). They substantially **de-risk but do not fully resolve** that blocker — see [Open Questions](#open-questions) below.

> ⚠️ **The OCR engine recommendation in this section was superseded on 2026-08-20.** It was made under the assumption that `requires-python = ">=3.14"` was fixed. Once that pin was treated as negotiable, the decision changed to **Python 3.13 + native PaddleOCR**. See [Follow-up Research](#follow-up-research-2026-08-20--ocr-engine-decision-re-opened-with-the-python-pin-negotiable) at the end of this document, which is the current decision of record. The row-reconstruction findings below are unaffected and still stand.

**OCR engine recommendation (superseded): RapidOCR (ONNX Runtime), not PaddleOCR, not Tesseract as primary.** The finding that drove it: **PaddleOCR is blocked outright by this project's `requires-python = ">=3.14"` pin** — `paddlepaddle` ships no Windows wheel past cp313. RapidOCR is PaddleOCR's own OCR models converted to ONNX, ships as `py3-none-any` + `onnxruntime` (which does have a cp314 Windows wheel), returns per-fragment **rotated 4-point polygons with confidence** (not axis-aligned boxes — this matters directly for wavy geometry), supports fully offline model pinning, and has a documented, lightweight PyInstaller packaging path. Tesseract (`pytesseract`) is recommended as a cheap same-day second-opinion baseline, not the shipped engine — it needs a bundled native binary, has near-zero table awareness, and its own docs say line segmentation degrades badly on skew. docTR is the credible fallback if table-structure output turns out to be essential, at the cost of a multi-GB PyInstaller bundle (PyTorch) and unverified Python 3.14 support.

**Row-reconstruction recommendation: a deterministic, anchored, locally-linear pipeline — not a pretrained table-structure model.** No available ML table model (Table Transformer, PP-Structure/SLANet, Surya, ClusterTabNet) is trained or validated on distorted/scanned tables — all are trained on born-digital or camera-photographed renders, and TATR's own maintainers disclaim scanned-table performance. The recommended approach: (0) global deskew, (1) OCR with rotated-quad fragments + confidence retained, (2) column bands from whole-page x-clustering, (3) **anchor-seeded, strip-by-strip row growth** with per-row RANSAC/Theil-Sen line fitting and a global non-crossing constraint, (4) redact in a straightened coordinate space that maps back to *original, unresampled* pixels, (5) **hard-gate anything ambiguous into FR-006's confirmation flow rather than silently resolving it**. The single most important architectural inversion: **redact by keep-list, not redact-list** — compute the one row to keep visible, destroy everything else, so a reconstruction error fails safe (visible over-redaction) rather than unsafe (a wrong row left exposed).

**Codebase is a clean slate for this work.** F-01 landed only CLI scaffolding — `inspect` is a zero-argument stub that exits 1. No OCR/image/PDF dependency has been added yet (`pyproject.toml` has only `typer`). Strict mypy is already on for `src/`, and `CLAUDE.md` already mandates typed domain models (Pydantic/dataclass, not dicts) for OCR fragments/rows — this is a hard constraint for S-01's design, not a suggestion. `pyproject.toml`'s `pytest` config already pre-registers a `slow` marker described as "fixture-heavy OCR or full-page redaction test," confirming this work was anticipated at bootstrap time. No prior change doc picks a library or algorithm — nothing to reconcile against.

## Detailed Findings

### Sample distorted scans (`context/test_images/`)

Six PNG files, each an "Przykład N" (Example N) labeled table mockup with 8 rows of a 5-column debtor table (Lp./Imię/Nazwisko, Adres, Kwota zadłużenia, Wierzyciel):

| File | Label | Distortion type |
|---|---|---|
| `1.png` | Przykład 1 | Clean scan, slightly tilted ("lekko pochylony") |
| `2.png` | Przykład 2 | Shadows + uneven lighting ("cieniami i nierównym oświetleniem") |
| `3.png` | Przykład 3 | Wavy/curved paper ("falowaniem kartki") |
| `4.png` | Przykład 4 | Low-quality: blurred, noisy ("rozmazany, z szumem") |
| `5.png` | Przykład 5 | Partially cut-off columns ("częściowo uciętymi kolumnami") |
| `7.png` | Przykład 6 (label/filename mismatch — no `6.png` exists) | Scan lines + artifacts ("liniami i artefaktami") |

These cover most of the geometric/quality distortion categories the PRD's row-reconstruction requirement worries about (FR-003), plus a partial-column-cutoff case not explicitly discussed in the PRD. They are **not** a photographed/scanned real document — the text is crisp and computer-rendered, only the paper/lighting/noise effects are synthetic. This is enough to build and exercise the reconstruction pipeline against a *controlled range* of distortions, but does not substitute for validating against a genuine real-world scan (see Open Questions).

### Current codebase state (F-01 baseline)

- `src/cover_data/cli.py` — `inspect` is a zero-argument `@app.command()` stub (no image-path argument exists yet — deliberately deferred to S-01's own plan), docstring `"""Show reconstructed table rows with OCR confidence flagged. (S-01)"""`, body calls a shared `_not_yet_implemented("S-01")` helper that echoes and exits 1.
- `src/cover_data/__init__.py` — 6 lines, `main()` only calls `app()`; must remain zero-arg per the PyInstaller build in `.github/workflows/release.yml`.
- `pyproject.toml` — `requires-python = ">=3.14"`; runtime deps: only `typer>=0.27.1`; dev deps: `mypy>=2.3.1`, `pytest>=9.1.1`, `ruff>=0.16.3`; `[tool.mypy] strict = true, files = ["src"]`; `[tool.pytest.ini_options]` pre-registers a `slow` marker — `"slow: fixture-heavy OCR or full-page redaction test"` — and lefthook's pre-commit hook filters with `-m "not slow"`, anticipating this exact work.
- `tests/test_cli.py` uses `typer.testing.CliRunner`, one test per behavior (exit code + output substring); no `tests/fixtures/` or `conftest.py` exists yet.
- No image/OCR/PDF library, sample data directory, or implementation code exists anywhere in the repo prior to this research (the `context/test_images/` discovery above is new as of this session).
- No prior change doc (`cli-entrypoint-scaffold`, `bootstrap-verification`) picks an OCR library or row-reconstruction approach — both explicitly deferred this decision to S-01.

### OCR engine comparison

**The Python 3.14 constraint reorders the whole comparison.** Verified against PyPI wheel metadata (2026-08-20):

| Package | cp314 Windows wheel? |
|---|---|
| `onnxruntime` 1.29.0 | Yes |
| `torch` 2.13.0 | Yes |
| **`paddlepaddle` 3.3.1** | **No — cp39 through cp313 only** |
| `tesserocr` 2.11.0 | cp314 exists but **no Windows wheels at all** |
| `pytesseract` 0.3.13 | Pure Python — fine |
| `rapidocr` 3.9.2 | `py3-none-any` — fine |
| `python-doctr` 1.0.1 | `py3-none-any` — fine, deps resolve on 3.14 |

- **Tesseract (`pytesseract`)** — `image_to_data()` gives per-word axis-aligned bbox + confidence (0–100) plus a free `block/par/line/word` grouping hint. Table awareness is essentially absent — Tesseract's own docs: *"tesseract has a problem to recognize text/data from tables... without custom segmentation/layout analysis"*; the one PR that exposed table structure via the API was reverted for crashes. Skew degrades line segmentation significantly per Tesseract's own guidance. Windows packaging needs a bundled native `tesseract.exe` + `tessdata/` (~60 MB), with the classic `TESSDATA_PREFIX` off-by-one-directory failure mode. `tesserocr` (in-process binding) is not viable on Windows (no wheels).
- **PaddleOCR / PP-StructureV3** — technically the strongest table story (dedicated cell-detection + structure-recognition models, `SLANet_plus` explicitly designed to tolerate table-position offset), but **blocked on Python 3.14** via `paddlepaddle`. Models are not bundled — full stack is several hundred MB to >1 GB downloaded on first run from HuggingFace/ModelScope/BOS.
- **docTR (Mindee)** — now ships a `table_predictor` (`tablecenternet`) returning per-cell row/col spans, and is the one candidate that explicitly advertises skew/rotation handling (`assume_straight_pages=False` → rotated polygons). `py3-none-any`, `requires_python >=3.10,<4`, deps resolve on cp314 — but **upstream classifiers stop at 3.12 and 3.14 support is unverified**. Biggest strike: it's a PyTorch stack (`torch`+`torchvision`+`onnx`+`opencv`+`scipy`) — a multi-GB PyInstaller bundle with a brittle hidden-imports fight.
- **EasyOCR** — ruled out: stale (last release Sep 2024), no word-level boxes, no table structure.
- **Surya 2** — ruled out for this deployment: v0.20+ requires spawning a `vllm`/`llama-server` inference backend (Docker+NVIDIA or `llama.cpp`), not viable inside a caseworker's Windows `.exe`; weights are also modified-OpenRAIL-M licensed, not plain Apache-2.0.
- **RapidOCR — the recommendation.** PaddleOCR's models converted to ONNX, served via ONNX Runtime, maintained by a separate team (RapidAI). `rapidocr` is `py3-none-any`; every dependency (`onnxruntime`, `opencv`, `numpy`, `shapely`, `pyclipper`) has a cp314 Windows wheel. Returns **4-point polygons per text region + per-fragment confidence score**, with `text_score`/`box_thresh`/`unclip_ratio` exposed at the call site — maps directly onto FR-002's confidence-flagging requirement. Offline model pinning is first-class (`model_root_dir`, `Det.model_path`, `Rec.model_path`, SHA256-checked in `default_models.yaml`). PyInstaller packaging is documented and lighter than a torch stack (ONNX Runtime, not torch). Companion `rapid-table` (also `py3-none-any`, works on 3.14) adds SLANet-family structure recognition if needed later — its sibling `wired-table-rec` is pinned `<3.13` and is **not** usable here.

**Two risks flagged as high-severity by the research:**
1. **Polish-language coverage is unverified.** A misrecognized diacritic (ą/ć/ę/ł/ń/ó/ś/ź/ż) breaks both FR-005's exact-match assumption and the redaction decision. Needs testing early against the sample images; may force a Polish-specific recognition model or Tesseract's `pol.traineddata`.
2. **First run downloads models from ModelScope**, which will hit the same TLS-inspecting-proxy problem already documented in `context/changes/bootstrap-verification/verification.md` (needs `--system-certs`/`UV_NATIVE_TLS=1`, or manual download + SHA256 check against `default_models.yaml`). The shipped `.exe` must ship weights pre-placed via `model_root_dir` — never fetch at runtime, both for the proxy and for the PII-must-not-leave-the-device invariant (weights themselves aren't PII, but a live model-download attempt on a caseworker's locked-down machine is a real deployment risk).

### Row-reconstruction approach

**Reframing that de-risks the whole problem:** this project doesn't need a general table parser. For one known 5-column template, it needs (a) a pixel band for the matched person's row, and (b) pixel bands for every other row to destroy. This licenses **redact by keep-list, not redact-list** — compute the one row to keep, overwrite everything else. A reconstruction error then fails *safe* (visible over-redaction the user rejects in the FR-007 preview) instead of *unsafe* (a neighbor's row wrongly left visible).

**Why naive y-clustering fails, concretely:** vertical drift across page width stays tolerable only while `W·tan(θ) < h/2`. For a 300dpi A4 scan (W≈2400px) with 30px rows, that's `θ < 0.36°` — beyond roughly one degree of tilt, naive y-bucketing already interleaves rows at opposite ends of the page. This is why global deskew is necessary but not sufficient (it removes tilt, not wave).

**No pretrained table-structure model is validated on distorted scans.** Table Transformer (TATR) is trained on born-digital PDF renders and its own maintainers disclaim scanned-table performance; a 2025 study found 46% of real scanned tables structurally erroneous out of the box. PaddleOCR's SLANet/SLANeXt self-report 59–70% accuracy on their own hard table set and explicitly warn their cell-position predictions can be invalid. Surya's table_rec has the same backend-deployment problem as its OCR. ClusterTabNet (SAP) is conceptually the closest prior art — rotation-agnostic pairwise same-row/same-column prediction — but is also trained on born-digital table datasets, useful as a *formulation* to borrow, not a model to deploy.

**Recommended five-stage deterministic pipeline** (full detail and sourcing in the sub-agent's report, condensed here):

0. **Global deskew** (`cv2.minAreaRect` on text mask, or Hough on ruling lines if present) — removes the affine tilt component; record the rotation matrix, don't discard it.
1. **OCR with rotated-quad fragments + confidence retained** — RapidOCR primary; keep Tesseract's independent `line_num` grouping as a cheap cross-check (disagreement between the two is itself a useful ambiguity signal).
2. **Column bands from the whole page** via 1-D gap-break clustering on x-positions (or projection-profile valleys) — columns are far more stable under wave than rows are, and with one known template the expected column count can be hard-asserted, not just inferred.
3. **Anchor-seeded, strip-by-strip row growth** — seed rows from the densest, single-line anchor column (surname/first-name), where horizontal span is narrow enough that wave is negligible; grow each row rightward strip-by-strip using local-linearity extrapolation (a curved baseline is well-approximated by a straight segment within a narrow vertical strip — the standard result behind most classical row-reconstruction work, e.g. `pdftabextract`, Meng et al. ICCV 2015); fit each row with a robust estimator (RANSAC/Theil-Sen) so one bad OCR fragment can't drag the row; **validate globally with a non-crossing constraint** — fitted row baselines must be monotone and never cross across the page width, which is a nearly free, high-value correctness check.
4. **Redact in a straightened coordinate space that maps back to unresampled original pixels** — represent row curvature as a per-row vertical offset field, do matching/banding in the straightened space, but map the resulting band polygon back to *original* pixel coordinates for the actual overwrite. This is important: dewarping the *image* itself (e.g. `page-dewarp`, PaddleOCR's UVDoc) resamples pixels, which is in direct tension with FR-009/the true-redaction invariant — dewarping should only ever be used to make OCR read better, never as the coordinate system the redaction itself happens in.
5. **Hard-gate ambiguity into FR-006's confirmation flow, don't silently resolve it** — cell count ≠ expected column count, any row-baseline crossing, row-height/spacing outliers beyond N·MAD of the page median, high-residual fragment assignment, Tesseract/RapidOCR grouping disagreement, low-confidence fragments in the matched row, or a fitted row count mismatching an independently-derived count (e.g. anchor-column cluster count) should all route to explicit user confirmation.

**The one-hour spike worth doing before building custom:** `img2table` (OpenCV-based, Python 3.14 support added, pluggable OCR backends including RapidOCR/Tesseract, returns cell-level bboxes, can run detection-only) against the real sample images — if it handles the distortion categories in `context/test_images/` adequately, it could save weeks; its own docs are honest that it's tailored to light/white backgrounds and historically weaker on borderless tables.

**Biggest limitation, stated plainly by the research:** the local-linearity assumption (step 3) has a cliff edge — smooth curvature (bowed/wavy paper, `Przykład 3`) is handled; **folding or creasing, where baselines have abrupt turnings, is not**, and no available pretrained dewarping model (all trained/benchmarked on camera-photographed deformation, not flatbed scans) reliably closes that gap. Which side of that line the project's real documents fall on is exactly the roadmap's blocking Open Question.

## Code References

- `src/cover_data/cli.py` — `inspect` stub, the attachment point for S-01's real implementation
- `src/cover_data/__init__.py` — entry point, must stay zero-arg (PyInstaller constraint)
- `pyproject.toml` — `requires-python = ">=3.14"` (the constraint that rules out PaddleOCR); `[tool.mypy] strict = true, files = ["src"]`; pytest `slow` marker pre-registered for OCR/redaction tests
- `tests/test_cli.py` — `CliRunner`-based test pattern to follow for new `inspect` tests
- `context/test_images/1.png` through `context/test_images/7.png` (six files, `6.png` missing) — sample distorted scans, newly discovered

## Architecture Insights

- **Typed domain models are a hard constraint, not a preference**, per `CLAUDE.md`: OCR fragments, cells, and rows must be Pydantic models or `@dataclass`, never raw dicts — this is explicitly because an untyped dict makes a fragment→cell→row shape mismatch invisible until runtime, which is precisely the failure mode this project exists to prevent.
- **Redact-by-keep-list** (compute the one row to preserve, destroy everything else) is the single highest-leverage architectural decision surfaced by this research — it converts every row-reconstruction failure mode from "silent privacy breach" into "visible, rejectable over-redaction," which aligns with FR-006 (no silent auto-pick) and FR-007 (preview before output) far better than a redact-list approach would.
- **Geometry must survive in original, unresampled pixel coordinates** through the whole pipeline — any dewarping step used to improve OCR quality must have its transform explicitly inverted before the redaction mask is applied to the source image, or FR-009/the true-redaction invariant is at risk.
- **Two independent groupings as a correctness signal**: since Tesseract's own `line_num` output and RapidOCR/whatever-is-chosen's own row hypothesis come from different code, their disagreement is a nearly-free ambiguity detector worth wiring into the FR-006 confirmation gate.

## Historical Context (from prior changes)

- `context/changes/bootstrap-verification/verification.md` — "Why this stack" section already names the three hard parts as *"OCR with per-fragment confidence, table-row reconstruction on distorted scans, and pixel-permanent redaction into a PDF"* and confirms local-only OCR is a hard constraint (hosted OCR APIs ruled out by the self-host deployment target). Also documents the TLS-inspecting-proxy issue (`--system-certs`/`UV_NATIVE_TLS=1`) that will resurface when adding OCR dependencies and downloading RapidOCR's ONNX model weights.
- `context/changes/bootstrap-verification/verification.md` "Project-specific follow-ups" already anticipated this slice: *"Add the real dependencies: OCR, image/geometry, and PDF libraries... as dependencies"* — flagged as open at bootstrap time, still open now.
- `context/changes/cli-entrypoint-scaffold/plan.md` — established the `@app.command()` / `Annotated[...]` typing convention new S-01 code must follow, and explicitly deferred `inspect <image>`'s argument signature to S-01's own plan.
- No prior change doc names an OCR library, image-processing dependency, or row-reconstruction algorithm — this research is the first pass at that decision.

## Related Research

None yet — this is the first research artifact for this project beyond `bootstrap-verification/verification.md` and the F-01 plan docs.

## Open Questions

1. **The roadmap's blocking Unknown is substantially de-risked but not fully resolved.** `context/test_images/` provides six *synthetic* distorted-scan mockups covering tilt, shadow/lighting, wave, blur/noise, column cutoff, and scan-line artifacts — enough to build and exercise the reconstruction pipeline against a controlled range of distortions. But the text in these samples is crisp and computer-rendered; a genuine photographed/scanned real debtor list may carry OCR-noise characteristics (ink bleed, genuine paper fold creases, print degradation) these mockups don't reproduce. Recommend treating S-01's plan as **unblocked to proceed** using these samples as the primary validation fixture, while flagging that a real scan — if one ever becomes available — should be run through the pipeline as a follow-up validation step before this slice is considered fully proven.
2. **Polish-language OCR accuracy for RapidOCR/Tesseract is untested.** Needs an early spike against `context/test_images/` before committing to a recognition model, since it affects both FR-005 (exact-match search) and the correctness of the redaction decision.
3. **Whether `img2table` (or another packaged table-extraction library) handles the sample distortion categories well enough to shortcut the custom Stage 3 pipeline** is unknown — worth the one-hour spike recommended above before committing to building anchor-seeded row growth from scratch.
4. **Folding/crease-style distortion is not represented in the current samples** (they cover tilt/wave/shadow/blur/cutoff/lines, not creasing) and is the one distortion category the recommended algorithm's local-linearity assumption cannot handle. Worth confirming this is genuinely out of scope for the real documents this tool will process, since if it isn't, Stage 3 as designed would need revisiting.

---

## Follow-up Research 2026-08-20 — OCR engine decision re-opened with the Python pin negotiable

**Trigger:** the `requires-python = ">=3.14"` pin was the sole reason PaddleOCR was ruled out in the first pass. Once the project owner confirmed the Python version is changeable if it buys a better OCR, the comparison had to be re-run. All claims below were verified by direct `uv pip compile` resolution runs and current upstream docs, not inferred.

### Correction to the first-pass finding

The first pass said "PaddleOCR is blocked by Python 3.14." That is **half right, and the half that's wrong matters**:

- `paddleocr` 3.7.0 + `paddlex` 3.7.2 **do resolve cleanly on Python 3.14** — 61 packages, and `paddlepaddle` is *not* among them. PaddleOCR 3.5+ decoupled the inference engine from the package (`engine` ∈ `paddle` / `transformers` / `onnxruntime`), so the framework is no longer a hard dependency. `paddleocr[doc-parser]` + `onnxruntime==1.29.0` also resolves on 3.14 (96 packages, no torch, no paddlepaddle).
- **But the ONNX path is a trap on 3.14.** PaddleOCR ships all official models in PaddlePaddle static-graph format only. Converting them to ONNX requires the Paddle2ONNX plugin, which itself requires `paddlepaddle` (and on Windows, the *nightly* build). So `engine="onnxruntime"` on Python 3.14 means bringing your own pre-converted ONNX models from a third party — which is precisely what RapidOCR is.
- `paddlepaddle` 3.3.1 confirmed: wheels for `cp39`–`cp313` only. On 3.13 the full stack (`paddleocr[doc-parser]` + `paddlepaddle==3.3.1`) resolves without complaint.

So the real choice is not "PaddleOCR vs RapidOCR" — RapidOCR *is* PaddleOCR's models, converted and re-hosted by a third party. The real choice is **first-party pipeline on 3.13 vs. third-party converted weights on 3.14.**

### Decision: move to Python 3.13 and adopt native PaddleOCR

Recommended, given the owner's explicit willingness to move the Python version:

**What the downgrade buys** (none of which RapidOCR provides):
- **UVDoc text-image unwarping** (~30 MB, ~870 ms CPU) — a learned dewarping model aimed squarely at *the* hard problem of this project (`Przykład 3`, wavy paper). This is the single strongest reason to take this path.
- **Document orientation classification** (~7 MB, 99.06% top-1) — free robustness on rotated inputs.
- **PP-StructureV3** layout + table cell detection, available as a cross-check signal (see caveat below).
- **Official first-party model distribution** with no conversion step, plus `PP-OCRv6` (default in PaddleOCR 3.7, +5.1% recognition / +4.6% detection over PP-OCRv5_server, single model covering 46 Latin-script languages).
- **Single-character coordinates** — PP-OCR series now supports returning per-character boxes, a finer geometric primitive than the first pass assumed was available.

**What it costs:**
- Python 3.14 → 3.13. Near-zero real cost: the codebase is one stub CLI file plus two test files and uses no 3.14-only feature. `.python-version`, `pyproject.toml`'s `requires-python`, and the CI/release matrix are the only touch points.
- `paddlepaddle` is a heavy runtime dependency and is materially harder to freeze with PyInstaller than ONNX Runtime. **This is the one genuine regression** and it lands on the `release.yml` `.exe` build, not on development.

**Mitigation for the packaging cost — develop on Paddle, ship on ONNX.** Because the 3.13 environment *can* run `paddle2onnx`, the export path is available as a build-time step: validate with the full first-party pipeline, then convert exactly the models actually used into ONNX and ship a lean `onnxruntime`-only runtime. This gets the best of both and is why the downgrade is not a one-way door. Keep the OCR engine behind a small `Protocol` yielding the typed `OcrFragment` so Paddle / ONNX / Tesseract stay swappable — the first pass already recommended this and it is now doing real work.

### Polish-language risk: resolved

The first pass flagged Polish diacritic accuracy as "the highest-severity unknown in the whole recommendation." It is now closed: Polish is explicitly supported (`lang="pl"`), served by `latin_PP-OCRv5_mobile_rec` — 14 MB, 84.7% accuracy, covering 47 Latin-script languages including Polish. Accuracy on *these specific scans* still needs an empirical check against `context/test_images/`, but there is no longer a question of whether a Polish-capable model exists.

### Why not the 2025/26 VLM-OCR wave (dots.ocr, DeepSeek-OCR, olmOCR, MinerU2.5, Granite-Docling, PaddleOCR-VL)

These models top the document-understanding leaderboards, and they are the wrong tool for this project — a conclusion worth recording explicitly so it isn't re-litigated:

- **They optimize transcription, not geometry.** The benchmarks they win (OmniDocBench and similar) measure document → Markdown/HTML fidelity. This project's deliverable is a *pixel region to destroy*. PaddleOCR's own documentation draws this exact line, noting that PP-StructureV3 — unlike the PaddleOCR-VL models — returns table cell coordinates and text coordinates.
- **They hallucinate.** A generative model that invents a plausible name or silently drops a row is a correctness catastrophe in a PII-redaction tool, where the failure is invisible in the output and the consequence is exposing a real person's debt record.
- **No calibrated per-fragment confidence.** FR-002 requires retaining and flagging per-fragment confidence; token logprobs from an autoregressive decoder are not the same thing and don't map onto "this bounding box is uncertain."
- **Deployment weight.** Sub-billion-to-multi-billion-parameter VLMs on a caseworker's CPU-only Windows laptop, inside a PyInstaller `.exe`, is not viable — and several (notably Surya 2) now require spawning a separate inference server process.

A VLM remains defensible in exactly one narrow future role: an optional second-opinion transcription used *only* to cross-check the deterministic pipeline's text and raise ambiguity into the FR-006 confirmation gate — never as the source of redaction geometry.

### Caveat carried forward, unchanged

Adopting PaddleOCR **does not** mean adopting PP-Structure as the row-geometry source. The first pass's finding stands: SLANet/SLANeXt self-report 59.5–69.7% on their own hard table set, upstream docs state SLANeXt cell predictions can be invalid, and every pretrained table model in this family is trained on born-digital renders rather than distorted scans. PaddleOCR is being adopted for **detection + recognition quality and document preprocessing**; the anchored, locally-linear row-reconstruction pipeline in Stage 3 above remains the plan, with PP-Structure output usable only as an optional disagreement signal feeding FR-006.

### Concrete plan delta for `/10x-plan`

1. `.python-version`: `3.14` → `3.13`; `pyproject.toml`: `requires-python = ">=3.13"`.
2. Re-lock (`uv lock --system-certs`) and re-run the full gate (`ruff`, `mypy --strict`, `pytest`) to confirm the downgrade is inert — expected, given the codebase size.
3. Update the CI and release workflows' Python version, and the stack notes in `CLAUDE.md` + `context/foundation/tech-stack.md` (which currently state 3.14).
4. `uv add --system-certs "paddleocr[doc-parser]" paddlepaddle` — note `--system-certs` is mandatory on this network, and PaddleOCR additionally pulls `opencv-contrib-python`, `shapely`, `pyclipper`, `pydantic`, and `pypdfium2` (the last of which usefully pre-stages the PDF-ingestion fast-follow).
5. Pin model directories explicitly (`text_detection_model_dir`, `text_recognition_model_dir`, `doc_unwarping_model_dir`) and pre-place weights; assert no network I/O at inference time, both for the PII invariant and because the TLS-inspecting proxy will otherwise break first-run downloads.
6. Set `lang="pl"` and benchmark recognition against all six images in `context/test_images/` before building Stage 3 — this is the empirical check that the Polish model is good enough for FR-005's exact-match assumption.
