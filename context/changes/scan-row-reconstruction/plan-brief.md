# Scan Row Reconstruction (S-01) — Plan Brief

> Full plan: `context/changes/scan-row-reconstruction/plan.md`
> Research: `context/changes/scan-row-reconstruction/research.md`

## What & Why

Build `cover-data inspect <image>`: run local OCR on a scanned debtor-list page, reconstruct the logical table rows, and show them with low-confidence fragments and geometric ambiguity flagged. This is the roadmap's north-star slice — it tests the assumption the whole product rests on, that row geometry can be resolved correctly as data even when the scan is distorted. If it fails, no later guardrail matters, because rows would already be attributed to the wrong person.

## Starting Point

`inspect` is a zero-argument stub that exits 1 (`src/cover_data/cli.py:37`). The only runtime dependency is Typer; no OCR, image, or geometry code exists. Six synthetic fixtures sit at `context/test_images/`, covering tilt, lighting, waviness, blur, cut-off columns, and scan artifacts. `tech-stack.md` has already locked the OCR engine (PaddleOCR, local, Python 3.13) but the pin has not moved yet — the codebase is still on 3.14.

## Desired End State

`inspect context/test_images/3.png` prints eight reconstructed debtor rows with their cell text, pixel row extents, confidence flags, and ambiguity flags. `--overlay out.png` writes a copy of the scan with the detected row and column bands drawn on it, so the geometry can be checked by eye. The source image is byte-identical afterwards, and no file other than an explicitly-requested overlay exists on disk when the command returns — on success, on failure, or on interrupt.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| --- | --- | --- | --- |
| OCR engine and Python version | PaddleOCR local, Python 3.13 | Already locked in `tech-stack.md`; verified during planning that the stack resolves on 3.13/Windows (97 pkgs, no torch). | Research |
| Row-extent source | Ruling lines primary, text clustering as cross-check | All six fixtures are fully-ruled bordered tables — a fact research missed; horizontal rules give row *extent* directly, which is what Risks #1/#2 turn on. | Plan |
| PRD Open Question #2 (layout) | Family of bordered debtor tables, per-document column detection | Keeps all six fixtures in scope including the only waviness sample and the sharpest Risk #1/#2 test; cheap once ruling lines are being found anyway. | Plan |
| Coordinate space | Commit now — unwarp is read-side only, transform always inverted | S-02/S-03 inherit a space that cannot silently violate FR-008/FR-009; the round-trip assertion is cheap now and near-impossible to retrofit. | Plan |
| Table library | Own it with OpenCV; no `img2table` | Keeps confidence retention and the coordinate contract under our control rather than a third party's. | Plan |
| Ground truth | Label `1.png`, `3.png`, `5.png` (~24 bands) now | A real code-independent oracle for the highest-risk fixtures at half the labelling cost. | Plan |
| Ambiguity handling | Detect and surface in S-01; gate in S-02 | Signals fall out of the geometry stage naturally; S-02 then only has to write a prompt. | Plan |
| Confidence flagging | Documented default + `--min-confidence`; flag never filters | Keeps "flagged" distinct from "discarded", and lets tests drive behavior by input rather than asserting the constant. | Plan |
| Artifact lifecycle | Nothing temporary at all — in-memory intermediates only | Makes Risk #3 structurally impossible rather than dependent on cleanup firing on the interrupt path. | Plan |

## Scope

**In scope:** Python 3.13 migration; PaddleOCR stack with pre-placed offline weights; typed `OcrFragment`/`Cell`/`TableRow` model behind an engine `Protocol`; ruling-line row and column geometry; ambiguity detectors; `inspect` CLI with terminal table and optional overlay; fixture manifest and hand-labelled ground truth for three fixtures.

**Out of scope:** search, matching, confirmation, preview (S-02); redaction and PDF output (S-03); PDF ingestion; PP-Structure or any ML table-structure model; `img2table`; ONNX export and PyInstaller work; OCR character-accuracy testing (`test-plan.md` §7); `--json` output; ground truth for `2.png`, `4.png`, `6.png`.

## Architecture / Approach

```
image path
  → OCR adapter (Paddle, behind Protocol)   → OcrFragment[]  ── original pixels, transform inverted
  → ruling-line extraction (OpenCV)         → RowBand[] + ColumnBand[]
  → cell assignment                         → TableRow[]
  → text clustering (independent)           → second row hypothesis
  → ambiguity detectors                     → signals on each row
  → rich terminal table + optional overlay PNG
```

The engine sits behind a `Protocol` so Paddle, a future ONNX runtime, and Tesseract stay swappable. The text-clustering path deliberately does not consume the ruling-line output — its independence is what makes disagreement a useful signal.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Python 3.13 + OCR stack | Pin moved, deps added, weights pre-placed, zero network I/O at inference | `paddlepaddle` install or offline model pinning fights the TLS proxy |
| 2. Fixture manifest + ground truth | ~24 hand-labelled row bands over three fixtures | Labelling is manual and is the rollout's most expensive asset |
| 3. Domain model + OCR adapter | Typed fragments, engine `Protocol`, coordinate contract | Paddle 3.x result field names differ from published 2.x docs |
| 4. Ruling-line geometry | Row extents and per-document column schema | `6.png`'s vertical streaks and `5.png`'s missing right border |
| 5. Ambiguity signals | Typed signals on every row for S-02 to gate on | Thresholds firing on every row would make them useless |
| 6. `inspect` CLI surface | Terminal table, overlay, no temp artifacts, source immutable | Paddle writing scratch files of its own accord |

**Prerequisites:** F-01 (done). Python 3.13 available via `uv`. `--system-certs` / `UV_NATIVE_TLS=1` on this network. Model weights provisioned into a git-ignored `models/`.
**Estimated effort:** ~4–6 sessions across six phases, with Phase 2 dominated by manual labelling and Phase 4 by threshold tuning.

## Open Risks & Assumptions

- **The ruling-line bet is fixture-specific.** All six samples are bordered, but a real scan with a borderless table, or with fold creases that break the rules, degrades to the text-clustering path alone.
- **The fixtures are synthetic.** PRD Open Question #1 remains open — crisp computer-rendered text does not reproduce ink bleed or print degradation. A green suite here is necessary, not sufficient, for calling S-01 proven.
- **Polish diacritic accuracy is unverified on these specific scans.** A model that exists is not a model that reads `ą/ł/ż` correctly here; this directly affects FR-005's exact-match assumption in S-02.
- **Fold/crease distortion is unrepresented** in the fixture set and is the one category neither ruling lines nor local-linearity handles.
- **`paddlepaddle` is heavy to freeze with PyInstaller** — the known regression, deferred to `release.yml` and the ONNX export path.
- **Stale doc:** `test-plan.md` §3 Phase 1 references `context/changes/testing-fixture-foundation/`, which does not exist; that work lands in Phase 2 here instead.

## Success Criteria (Summary)

- A user points the tool at any of the six fixtures and sees eight correctly-reconstructed debtor rows, with uncertain OCR visibly marked rather than silently trusted.
- The drawn overlay confirms row bands sit on true row boundaries — including on the wavy scan and the one whose right column runs off the page.
- The source file is provably untouched and the working tree carries no stray artifacts, on every path including failure and interrupt.
