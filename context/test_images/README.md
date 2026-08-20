# Test images

Sample debtor-list scans for building and exercising S-01 (row reconstruction),
S-02 (search + confirm) and S-03 (selective redaction).

**No real personal data.** Every name, address, amount and creditor is
placeholder. Creditors are fictional entities. The set is safe to commit.

## Identity comes from `manifest.json`, not from the filename

`manifest.json` is the authoritative index. Filename-derived identity has
already been wrong once in this directory (`test-plan.md` §2 finding 4), so
read the manifest and key off `filename`; the in-page `Przykład N` title is the
human-readable label.

## Two generations

| Files | Origin | Ground truth |
|---|---|---|
| `1.png`–`6.png` | image model, committed in `3f451c5` | **none** — never hand-labelled; `ground_truth_rows` is `null` |
| `7.png`–`24.png` | `generate_edge_cases.py` | **exact by construction** — every row is in the manifest |

The original six are a distortion ladder (tilt, lighting, waviness, blur,
cut-off columns, scan lines). The generated eighteen are edge cases: each one
targets a named failure scenario from `context/foundation/test-plan.md` §2, and
carries its rationale in the manifest's `why_this_edge_case`.

## What each generated fixture is for

| File | Edge case | Primarily exercises |
|---|---|---|
| `7.png` | two rows with the identical name `Anna Nowak` | FR-006 — no silent auto-pick |
| `8.png` | `Jan Kowalski` vs `Jan Kowalski-Nowak`, `Kowalska`, `Kowal` | FR-005 — exact match, not substring |
| `9.png` | diacritic-heavy surnames (ł, ż, ą, ś, ć) | Risk #4 — OCR folding diacritics |
| `10.png` | searched person absent; every row a near-miss | zero-match path, no output written |
| `11.png` | strong waviness (the amplitude `3.png` lacks) | Risks #1/#2 — band vs. curved row |
| `12.png` | −6.8° skew + dark scanner border | deskew before row detection |
| `13.png` | phone-photo keystone + shadow | rows are trapezoids, not rectangles |
| `14.png` | rows 2/4/6 wrap to 3–4 lines | breaks fixed row-pitch assumptions |
| `15.png` | 22 rows, 12pt, ~24px pitch | off-by-one row selection |
| `16.png` | no ruling lines at all | row finding must not depend on rules |
| `17.png` | crease pinch + shadow band across rows | shadow read as a rule line |
| `18.png` | 26 rows laid out, sheet ends inside row 23 | bottom-edge truncation (vertical twin of `5.png`) |
| `19.png` | header + exactly one row | degenerate: zero redaction bands |
| `20.png` | header only, no data rows | header must not count as a row |
| `21.png` | blank row 6, missing cells elsewhere | blank row must not collapse the index |
| `22.png` | stamp, biro annotation, punch holes | non-table ink crossing row boundaries |
| `23.png` | two tables, both numbered from 1 | row identity must carry its table |
| `24.png` | pale photocopy, JPEG q30, small | FR-002 — low-confidence flagging |

## Search scenarios

Each generated fixture carries `search_scenarios` — query, expected match
count, expected row indices, and a `must` note stating the behaviour under
test. These are the oracle: they were written against the fixture, not lifted
from an implementation. Several encode a decision that is **still open** (for
example, whether a de-diacriticised query matches, or whether a row with no
given name is addressable by surname alone) — the `must` text says so.

## Regenerating

Pillow and numpy are deliberately not project dependencies; this is fixture
tooling, not product code.

```bash
uv run --with pillow --with numpy --no-project \
    python context/test_images/generate_edge_cases.py
```

Output is deterministic (fixed RNG seeds), so regenerating without editing the
script produces identical bytes. The run ends with a `verify()` pass that fails
if any declared scenario disagrees with the rows actually rendered — so the
manifest cannot silently drift from the images.

`1.png`–`6.png` are not regenerated and are never touched by the script.

## Known limitation

This set is entirely synthetic. It is enough to build against and to catch
regressions, but it does **not** close the PRD's blocking open question, which
asks for a *real* representative distorted scan. Risks #1 and #2 can be
exercised here; they cannot be declared closed here.
