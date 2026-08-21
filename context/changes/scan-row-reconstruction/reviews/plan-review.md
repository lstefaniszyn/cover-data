<!-- PLAN-REVIEW-REPORT -->
# Plan Review: Scan Row Reconstruction (S-01)

- **Plan**: `context/changes/scan-row-reconstruction/plan.md`
- **Mode**: Deep
- **Date**: 2026-08-21
- **Verdict**: REVISE → SOUND after triage
- **Findings**: 3 critical, 2 warnings, 3 observations

## Verdicts

| Dimension | Verdict | After fixes |
|-----------|---------|-------------|
| End-State Alignment | FAIL | PASS |
| Lean Execution | PASS | PASS |
| Architectural Fitness | PASS | PASS |
| Blind Spots | FAIL | PASS |
| Plan Completeness | WARNING | PASS |

Two FAIL dimensions points toward RETHINK by the letter of the rubric, but the plan's structure, phasing and Progress contract were sound throughout — all three critical findings had narrow, identified fixes that did not move a phase boundary. REVISE was the honest call, and all five accepted fixes have been applied.

## Grounding

10/10 paths ✓ · 4/4 symbols ✓ (`cli.py:37` inspect stub, `slow` marker, mypy `strict`, both workflows read `.python-version` via `setup-uv`) · brief↔plan ✓ · Progress 7/7 phases, 67/67 criteria mapped, 0 stray checkboxes ✓ (69/69 after fixes)

No `context/foundation/lessons.md` and no `docs/reference/contract-surfaces.md` exist — both checks skipped.

## Findings

### F1 — Cell-text equality assertion contradicts the plan's own OCR-accuracy exclusion

- **Severity**: ❌ CRITICAL
- **Impact**: 🔬 HIGH — architectural stakes; think carefully before deciding
- **Dimension**: End-State Alignment
- **Location**: Desired End State; Phase 5 criterion 5.2; "What We're NOT Doing"
- **Detail**: The plan excluded OCR character-accuracy testing per `test-plan.md` §7 ("the engine is not ours to fix; the only thing we control is whether we flag what it is unsure about"), then asserted exact cell-text match on all 20 generated fixtures — including `24.png`, which the generator comments is "tuned to be marginal, not illegible" at contrast 0.55 + JPEG q30, and `9.png`, whose own manifest `must` reads "match despite OCR diacritic folding, **or flag low confidence rather than report 0 matches**". The fixture's own oracle was looser than the plan's criterion, and the Phase 5 gate could not pass as written.
- **Fix A**: Structural correspondence + normalized comparison with a per-fixture allowance; exact equality only on clean fixtures.
  - Strength: Catches misattribution and within-row drift on all 20 fixtures.
  - Tradeoff: Introduces a tunable knob (Risk #2's named anti-pattern), and diacritic-folding normalization would silently cancel `9.png`'s purpose.
  - Confidence: HIGH — exclusion explicit in two documents.
  - Blind spot: Allowance cannot be set until Phase 4's manual check measures the engine.
- **Fix B**: Drop cell-text assertions entirely; geometry and counts only.
  - Strength: Zero contradiction, no knob.
  - Tradeoff: Loses the correct-geometry-wrong-assignment failure class.
  - Confidence: MEDIUM.
  - Blind spot: `21.png`'s blank-row-index case would go untested.
- **Fix C** (raised during triage, not in the original report): best-match each reconstructed row to a ground-truth row by string similarity across all cells; assert the assignment is the identity permutation.
  - Strength: Tests attribution directly — the actual product risk — robust to character errors by construction, with no per-fixture allowance. Leaves `9.png`'s diacritic purpose intact.
  - Tradeoff: Needs a stated tie-break for `7.png`'s two identical `Anna Nowak` rows; weaker than A at within-row cell drift.
  - Confidence: HIGH.
  - Blind spot: Within-row drift is covered elsewhere — cell-count mismatch in 5.1 and the Phase 6 unassigned-fragment signal.
- **Decision**: FIXED via Fix C. Added a "Row attribution, not string equality" section under Critical Implementation Details, rewrote Desired End State and criterion 5.2, and restated the §7 exclusion in "What We're NOT Doing" with the reason no assertion compares strings for equality.

### F2 — The geometry-mask mechanism assumes a geometric/photometric split the generator does not have

- **Severity**: ❌ CRITICAL
- **Impact**: 🔬 HIGH — architectural stakes; think carefully before deciding
- **Dimension**: Blind Spots
- **Location**: Phase 3, change 1
- **Detail**: Phase 3's entire ground-truth oracle rested on pushing a mask through "the geometric operations only." Confirmed at the line level that this split does not exist and three listed ops are wrong for a mask: `fold` (`generate_edge_cases.py:379`) applies the geometric pinch *and* the crease shadow in one function; `fit_page` (`:707`) derives its crop from image content (`inked = np.where(arr.min(axis=1) < 200)`), so a mask carrying only rule lines crops differently and misaligns every exported coordinate; `rotate` (`:396`) uses BICUBIC with `fillcolor=PAPER` and `downsample` (`:703`) uses LANCZOS, both of which blur a 1px mask line into a biased position while a bright fill reads as content. The failure mode is ground truth that is plausible but subtly wrong — every Phase 5 assertion then validates against a bad oracle and reports green.
- **Fix A ⭐ Recommended**: State the mask contract explicitly — split `fold`, inherit the page's crop box, NEAREST resampling with zero fill everywhere, plus an identity round-trip criterion.
  - Strength: Turns three silent corruption paths into stated contracts; the round-trip is a cheap test catching the whole class.
  - Tradeoff: Splitting `fold` must not change `17.png`'s bytes — already guarded by criterion 3.1.
  - Confidence: HIGH — all three confirmed at the line level.
  - Blind spot: `perspective` (`13.png`) not inspected for content dependence; takes an explicit quad, probably safe, unverified.
- **Fix B**: Abandon the mask; compose analytic point-transforms per operation.
  - Strength: No resampling in the geometry path.
  - Tradeoff: Requires inverting `wave` and `perspective` analytically — the exact risk the plan already warns about; touches ~20 fixture functions.
  - Confidence: MEDIUM.
  - Blind spot: `fit_page`'s content dependence remains either way.
- **Decision**: FIXED via Fix A. Added the evidence to Critical Implementation Details, added a four-clause "mask contract" to Phase 3 change 1 (including the unverified-`perspective` caveat), and added the identity round-trip as criterion 3.2.

### F3 — Row identity left undefined against three incompatible shapes of the manifest `index` field

- **Severity**: ❌ CRITICAL
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Plan Completeness
- **Location**: Phase 4 change 2; Phase 5 criteria 5.2–5.4; Phase 7 criterion 7.3
- **Detail**: The plan stated identity is `(table index, row index)` but never mapped it onto `ground_truth_rows[].index`, which takes three shapes: `'A1'`…`'B4'` on `23.png` (table already encoded, and `search_scenarios` uses `expected_rows: ["B1"]`); `'1'`, `'2'`, `None` on `21.png`, whose whole purpose is that a blank row must not collapse the index; and `'6'`, `'7'`, `'8'` on `26.png`, a continuation page where the rendered `Lp.` is *not* the positional index. Layout C has no `Lp.` column at all. Which reading "row index" means decides what S-03 redacts and what the overlay labels.
- **Fix**: Define positional index (model-owned, zero-based, always present) and recognized `Lp.` value (an ordinary cell under the `lp` role, possibly absent, `None`, or non-monotonic) as separate things; manifest comparison keys on position.
  - Strength: Removes a guess the implementer would otherwise make three inconsistent ways; layout C's missing `Lp.` column already proves position cannot come from the page.
  - Confidence: HIGH — all three shapes confirmed by reading the manifest.
  - Blind spot: S-02 needs the reverse translation for `expected_rows`; noted in the plan for the roadmap rather than solved here.
- **Decision**: FIXED. Phase 4 change 2 now defines both concepts and maps all three manifest shapes onto position explicitly; criteria 4.4, 5.4 and 7.3 updated to match.

### F4 — `verify()`'s ink check samples the post-photometric image, where "is this ink" is unreliable

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Blind Spots
- **Location**: Phase 3, change 4
- **Detail**: The check was specified against "the final image". Photometric ops run after geometric ones, and two fixtures break the premise: `24.png` applies `contrast(gain=0.55, offset=26)` then JPEG q30, so ink lands near 26 and paper compresses toward 161 — a fixed threshold is guesswork; `12.png` adds `scanner_border(level=32)`, so a boundary near the page edge sits on dark pixels and **passes for the wrong reason**, a false green on the oracle itself.
- **Fix**: Run the ink check against the pre-photometric render (which the mask mechanism already holds), keeping only a loose relative-darkness sanity check on the final image.
  - Strength: The check then tests what it claims, independent of subsequent degradation.
  - Tradeoff: Requires the generator to retain the pre-photometric image — already implied by the mask mechanism.
  - Confidence: HIGH — both fixtures' parameters read from source.
  - Blind spot: None significant.
- **Decision**: FIXED. Phase 3 change 4 rewritten with the evidence and the explicit "do not run this against the final image" instruction; criterion 3.3 updated.

### F5 — Pixel tolerance deferred twice and never defined

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 5 criterion 5.1; Testing Strategy
- **Detail**: "within a stated pixel tolerance" appeared twice with no value and no rule for choosing one — the obvious escape hatch, given `test-plan.md` Risk #2 warns about assertions satisfiable by loosening. Fixtures span 760px to 1240px wide with row pitches from ~24px (`15.png`) to full-size, so one absolute number cannot serve both.
- **Fix**: Express tolerance as a fraction of the fixture's own median row height, with a stated starting value.
- **Decision**: FIXED. Criterion 5.1 now specifies a starting tolerance of 0.15 × that fixture's median row height, and requires any change to be recorded with its reason.

### F6 — Two criteria assert almost nothing

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 1 criterion 1.1; Phase 5 criterion 5.10
- **Detail**: 1.1 ("full gate stays green on an unchanged codebase") is vacuously true for a doc-only phase. 5.10's "row count is stable across runs" asserts OCR determinism, not correctness.
- **Fix**: Replace 1.1 with a link-integrity check across the edited foundation docs; state 5.10's weakness explicitly as the price of those fixtures having no ground truth.
- **Decision**: FIXED. 1.1 is now a link/path resolution check. The `1.png`–`6.png` criterion now asserts a table is found, roles resolve, row count ≥ 1, and rows are non-overlapping and monotone — with an explicit note that this is deliberately weak and must not be strengthened by hand-labelling.

### F7 — Field-scoped scenarios added but never checked as satisfiable

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: End-State Alignment
- **Location**: Phase 3 change 3; Phase 5 success criteria
- **Detail**: Phase 3 adds `imie`/`nazwisko`/`pesel` scenarios to the manifest, but nothing in S-01 confirmed the roles those queries need actually resolve on those fixtures — a last-mile gap between "S-01 enables search" and evidence that it does.
- **Fix**: Add one Phase 5 criterion — every fixture carrying a field-scoped scenario resolves the role that scenario names.
- **Decision**: FIXED. Added as a Phase 5 automated criterion.

### F8 — Phase 5 carries seven change groups and 14 criteria

- **Severity**: 💡 OBSERVATION
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Lean Execution
- **Location**: Phase 5
- **Detail**: Thematically cohesive but cannot be committed until all seven parts work, which is a long red window. The row-strategy half and the column-roles half have no ordering dependency on each other.
- **Fix**: Split into 5a (row strategies + selector) and 5b (column roles + multi-table segmentation).
- **Decision**: SKIPPED — phase left whole as thematically cohesive.
