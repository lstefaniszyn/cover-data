---
project: "Cover the Data"
version: 1
status: draft
created: 2026-08-19
updated: 2026-08-21
context_type: greenfield
product_type: cli
target_scale:
  users: small
  qps: low
  data_volume: small
timeline_budget:
  mvp_weeks: 3
  hard_deadline: null
  after_hours_only: true
---

## Vision & Problem Statement

Debt-collection and debt-management organizations receive scanned PDF lists of debtors — often low-quality scans where table rows and columns are skewed, wavy, or unevenly spaced rather than clean grids. When a caseworker or compliance analyst needs to share information about one specific person from such a list (e.g. in response to a legal or business request) while keeping every other listed person's personal data hidden, no existing tool does this well: the data exists only as pixels, not searchable text, so today the analyst manually redacts every other row in an image or PDF editor — slow, and error-prone specifically because distorted table geometry makes it easy to miss part of a row or mis-attribute a cell to the wrong person.

Existing OCR-and-redact tooling assumes documents are clean, aligned grids; it can extract text or black out fixed regions, but it has no concept of "this row belongs to this person" once row boundaries stop being straight lines. The insight behind this project is that reliable person-selective redaction depends on treating row/table geometry as data that must be resolved correctly even when scans are distorted — get that wrong, and the tool either exposes someone who should stay hidden or blacks out the one person who was supposed to remain visible, which defeats the tool's entire purpose.

## User & Persona

A caseworker or compliance analyst working inside a single debt-collection / debt-management organization. They receive scanned PDF debtor lists from external creditors, and periodically need to produce a redacted version of a specific list that keeps one named person's data visible while hiding every other listed person's data, for use in a specific case, dispute, or external request. This is an internal tool for their org, not a multi-tenant product (for now — see Non-Goals).

## Success Criteria

### Primary
- Given a scanned PDF debtor list in one representative document layout, a user can search for a person by first/last name and generate a redacted PDF that keeps that person's row visible while every other row's personal data is truly redacted (not recoverable via text extraction).

### Secondary
- A basic audit log records who searched for/generated what, and when.

### Guardrails
- Redacted data must not be recoverable via text extraction or similar trivial techniques — true redaction, not a visual cover-up.
- The original source document is never modified; the anonymized output is always a separate artifact.

## User Stories

### US-01: User redacts all but one person from a scanned debtor list

- **Given** a caseworker has a scanned image of a debtor-list page on disk, in the one supported document layout
- **When** they point the tool at that image, search for a person by name, confirm the correct match, and request the anonymized output
- **Then** they receive a new PDF in which the matched person's row is fully visible and every other row's personal data is permanently redacted at the pixel level, unrecoverable, while the original source image is untouched

#### Acceptance Criteria
- The matched person's row is byte-for-byte visible in the output — no degradation, no accidental partial redaction
- Every other row's data is unrecoverable from the output by any trivial means (copy-paste, text extraction, zoom/contrast tricks on a visual-only cover)
- If the search matches more than one row, the user is required to confirm before output is generated — no silent auto-pick
- The original source image file is unchanged after the operation

## Functional Requirements

### Ingestion & processing
- FR-001: User points the system at an image file already on disk (one scanned document page). No upload flow or PDF-to-image conversion for v1. Priority: must-have
  > Socrates: Counter-argument considered: real debtor lists arrive as scanned PDFs, so skipping PDF entirely just defers that work. Resolution: kept as the deliberate MVP shortcut; PDF ingestion (render pages → images) is captured as an explicit fast-follow, not dropped.
- FR-002: System runs OCR on the image, retaining per-fragment text, bounding-box coordinates, and a confidence score; low-confidence fragments are flagged rather than silently trusted. Priority: must-have
  > Socrates: Counter-argument considered: OCR without a confidence value gives no way to flag a likely misread (e.g. a digit in an amount) — wrong-but-confident data is worse than none. Resolution: accepted; confidence score folded into the FR.
- FR-003: System reconstructs logical table rows from OCR fragments, tolerant of moderate misalignment, for the one supported document layout. Priority: must-have
  > Socrates: Counter-argument considered: "moderate misalignment" is undefined, risking a row-reconstruction approach that still silently fails on the exact wavy-scan problem this project exists to solve. Resolution: no fixed numeric tolerance pinned here (implementation parameter); instead tracked as an Open Question — validate against a real representative distorted scan, not a synthetic clean one.

### Search & matching
- FR-004: User can search for a person using a single free-text query, matched against `Imię` (given name), `Nazwisko` (surname), `Imię i nazwisko` (full name), or `PESEL` — selected via an explicit `--field` option that defaults to full name when omitted. Priority: must-have
  > Socrates: Counter-argument considered: separate first/last fields add UI complexity for little MVP benefit. Resolution: accepted; collapsed to one free-text field per selected search field, not one field per column.
  > Socrates: Counter-argument considered: defaulting to full name when `--field` is omitted is a silent inference, which sits uneasily beside the no-silent-auto-pick invariant (FR-006). Resolution: the default is a *documented, fixed* interpretation of an unqualified query, not a guess about which field the user meant — shape-based auto-detection (e.g. treating an 11-digit query as PESEL) is the guess, and it is rejected. This also preserves all 24 existing `search_scenarios` fixture scenarios (`context/test_images/manifest.json`) as written.
- FR-005: System returns the matching row and person location within the image for a search (exact match only for v1, against the field selected by FR-004). For `--field pesel`, both the query and the cell value are reduced to digits before comparison; a PESEL checksum failure never rejects a query. Priority: must-have
  > Socrates: Counter-argument considered: OCR misreads (even one character) can break exact match, making the MVP unreliable even on its own supported layout, independent of table geometry. Resolution: kept as written; tied to the same Open Question as FR-003 — validate against a real representative distorted scan, and revisit exact-match-only if OCR noise proves it unreliable there.
  > Socrates: Counter-argument considered: a checksum is free input validation — reject a PESEL that fails it before even searching. Resolution: rejected; OCR misreads a digit far more often than a real debtor list carries an invalid PESEL, so a checksum gate would reject valid searches for a fault in the reader, not the data. The checksum is retained as available evidence of OCR error (surfaced as an ambiguity signal), never used as a filter.
- FR-006: User can select/confirm the correct match when a search returns more than one row. Priority: must-have
  > Socrates: Counter-argument considered: duplicate names are probably rare, so "first match wins" could save a confirmation step. Resolution: kept as must-have; silent auto-pick on an ambiguous match risks violating the core guardrail (right person stays visible, everyone else hidden) — a confirmation click is cheap insurance against a wrong redaction.
- FR-007: User sees a preview of the matched row/person before final output is generated. Priority: must-have
  > Socrates: Counter-argument considered: as originally scoped nice-to-have, this could get cut under time pressure — but with no preview at all, a bad OCR/row match could silently ship the wrong person's data exposed, conflicting with the accuracy guardrail. Resolution: promoted to must-have.

### Redaction & output
- FR-008: System generates a redacted version of the image — the selected person's row stays visible, every other row's pixels are permanently overwritten so the underlying content is unrecoverable — and wraps it into an output PDF. Priority: must-have
  > Socrates: Counter-argument considered: permanent overwrite means a bad OCR/row-detection mistake becomes unrecoverable and unauditable after the fact. Resolution: kept as written — because FR-009 guarantees the source image is untouched, a bad redaction is correctable by simply re-running the process from source; a separate audit/undo record isn't needed and would also cut against data minimization.
- FR-009: The original source image is never modified; the output PDF is always a separate artifact. Priority: must-have
  > Socrates: Counter-argument considered: this may just restate FR-001 (the system only ever points at/reads the file). Resolution: kept as written and explicit — "points at a file" doesn't guarantee read-only behavior at the implementation level, so this stays a distinct, testable requirement rather than an assumption.

## Non-Functional Requirements

- Temporary artifacts created during processing (rendered images, intermediate OCR output) do not persist indefinitely — they are removed once the request that created them completes.

## Business Logic

Given a document and a selected target person, the system decides, row by row, whose data stays visible and whose gets redacted — by tying OCR-extracted identity back to table-row geometry, even when that geometry is imperfect.

The rule consumes two user-facing inputs: the document (an image containing a table of people and their associated data) and a search query naming the target person. Its output is a classification of every row into exactly one of two states — "belongs to the target person, stays visible" or "belongs to someone else, gets redacted." The user encounters this rule at the moment they confirm a search match and request the anonymized output: everything downstream (which pixels get blacked out, what the final output looks like) is a direct consequence of this row-level ownership decision.

## Access Control

Single user, single device for the MVP — no authentication layer. The org may have multiple caseworkers eventually, but v1 targets one person operating the tool directly. Role separation (e.g. admin vs. caseworker) is moot at this scale and deferred (see Non-Goals).

## Non-Goals

- **Arbitrary document layouts** — only the one representative layout is supported for v1; other formats are explicitly out of scope until this one is proven.
- **Handwritten documents** — only printed/typed table content is supported; handwriting recognition is a materially different, harder problem.
- **Multi-user / roles** — the MVP is single-user, single-device with no auth or role separation (see Access Control); multi-tenant support is deferred.

## Open Questions

1. **Partially resolved 2026-08-20, expanded 2026-08-21 — a sample set exists; a real distorted scan does not.** Six sample scans live at `context/test_images/` (`1.png`–`6.png`): a deliberate distortion ladder covering tilt, uneven lighting and shadows, page waviness, blur and noise, columns cut off at the page edge, and scan lines/artifacts — eight debtor rows each, placeholder names, no ground truth. As of 2026-08-21 these sit alongside 20 more fixtures (`7.png`–`26.png`, `context/test_images/manifest.json`) generated by `generate_edge_cases.py` with exact-by-construction row content and geometry, targeting named failure scenarios rather than a distortion ladder. Together this is enough to build and exercise row reconstruction against, so **it no longer blocks starting the work**.
   It is **not** enough to close the question as originally asked, even with the expanded set. However exact its ground truth, the generated set is still synthetic — precisely the "clean synthetic one" this question warned against — and no generator reproduces real ink bleed, print degradation, or scanner optics, so FR-003 and FR-005's exact-match assumption remain unvalidated against the real problem.
   **Residual question** — Owner: user: can a real representative distorted scan be obtained before FR-003 and FR-005 are treated as proven?

2. **Resolved 2026-08-21, during `scan-row-reconstruction` planning.** "The one supported document layout" is read as a **family of bordered debtor tables with per-document column detection**, not a fixed column schema — resolving the choice originally posed below. This keeps layouts A (`Lp.` + split `Imię`/`Nazwisko`), B (`Lp.` + merged `Imię i nazwisko`), and C (no `Lp.`, split name) all in scope, at the cost of harder cell attribution and column-role resolution, which S-01 (`scan-row-reconstruction`) delivers as the enabling contract for FR-004's `--field` option. Original framing, retained for record:
   > Variant **A** (`Lp.` column plus separate `Imię` / `Nazwisko` columns, six in total): `1.png`, `3.png`. Variant **B** (`Lp.` plus a merged `Imię i nazwisko` column, five in total): `2.png`, `4.png`, `6.png`. Variant **C** (no `Lp.` column, split name, five in total, last column truncated at the page edge): `5.png` alone. FR-003 and FR-005 are both written against *one* layout, and Non-Goals scopes v1 to one — but the available samples contain three. Two readings were open: a **fixed column schema**, in which case one variant is chosen and the rest become out-of-scope negatives (note that picking B discards both the only waviness sample and the sharpest cut-off-column sample); or a **family of bordered debtor tables with per-document column detection**, which keeps all samples in scope at the cost of harder cell attribution and a harder exact-match name lookup under FR-005.
