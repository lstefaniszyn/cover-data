---
project: "Cover the Data"
version: 1
status: draft
created: 2026-08-19
updated: 2026-08-19
prd_version: 1
main_goal: quality
top_blocker: decisions
---

# Roadmap: Cover the Data

> Derived from `context/foundation/prd.md` (v1) + auto-researched codebase baseline.
> Edit-in-place; archive when superseded.
> Slices below are listed in dependency order. The "At a glance" table is the index.

## Vision recap

Debt-collection caseworkers receive scanned debtor lists where table rows are skewed or wavy, not clean grids. When they need to share one named person's data while keeping everyone else on the list hidden, no existing tool ties OCR'd text back to "this row belongs to this person" once row boundaries stop being straight lines — so today that redaction is done by hand, slowly and with real risk of exposing the wrong row. This tool exists to make that row-to-person link reliable even when the scan geometry is imperfect, and to make redaction permanent rather than a cosmetic cover-up.

## North star

**S-01: User can point the tool at a scanned debtor-list image and see the reconstructed table rows, with OCR confidence flagged on low-confidence fragments.** — This is the smallest end-to-end slice that tests the assumption the whole project depends on: that row/table geometry can be correctly resolved as data even when a scan is distorted. If this fails on a real scan, no later guardrail (permanent redaction, exact-match search) matters, because rows would already be misattributed to the wrong person.

> "North star" here means the smallest end-to-end slice whose successful delivery proves the core idea works — placed as early as its Prerequisites allow, because everything sequenced after it only matters if this one holds up.

## At a glance

| ID   | Change ID                 | Outcome (user can …)                                                                   | Prerequisites | PRD refs                    | Status  |
| ---- | -------------------------- | ---------------------------------------------------------------------------------------- | -------------- | ---------------------------- | ------- |
| F-01 | cli-entrypoint-scaffold    | (foundation) invoke the tool as a real CLI command instead of a stub                     | —              | tech-stack.md CLI decision   | ready   |
| S-01 | scan-row-reconstruction    | point the tool at a scanned image and see reconstructed rows with OCR confidence flagged | F-01           | FR-001, FR-002, FR-003, US-01, NFR | blocked |
| S-02 | person-search-confirm      | search rows by name and confirm/preview the matched row before proceeding                | S-01           | FR-004, FR-005, FR-006, FR-007, US-01 | proposed |
| S-03 | selective-redaction-output | generate an output PDF where the confirmed match stays visible and every other row is permanently redacted, source untouched | S-02 | FR-008, FR-009, US-01, NFR | proposed |

## Baseline

What's already in place in the codebase as of `2026-08-19` (auto-researched + user-confirmed).
Foundations below assume these are present and do NOT re-scaffold them.

- **Frontend/interface:** absent — no CLI framework wired yet; `main()` is a one-line stub. The project deliberately uses terminal + OS image viewer as its interface (per `tech-stack.md`), not a web UI.
- **Backend / core logic:** absent — no OCR, row-reconstruction, search, or redaction code exists yet; `src/cover_data/__init__.py` is the only source file.
- **Data:** absent by design — the PRD needs no database (single-user, file-in/file-out); no ORM/DB driver in dependencies.
- **Auth:** absent by design — PRD Access Control and `tech-stack.md` both specify single-user, no auth layer for MVP.
- **Deploy / infra:** present — `.github/workflows/ci.yml` (lint/test/typecheck) and `release.yml` (PyInstaller Windows `.exe` on tag push); `lefthook.yml` mirrors CI locally; self-host deploy target declared.
- **Observability:** absent — no logging library; the PRD's "basic audit log" is a Secondary success criterion only, never promoted to a functional requirement (see Open Roadmap Questions).

## Foundations

### F-01: CLI entrypoint scaffold

- **Outcome:** (foundation) the project has a real, invokable CLI command surface — `fastapi`/`uvicorn` (inherited from an unrelated project and explicitly flagged as surplus) are removed, and a CLI framework is wired as the entrypoint.
- **Change ID:** cli-entrypoint-scaffold
- **PRD refs:** `tech-stack.md` ("uv remove fastapi uvicorn and add a CLI framework instead... if you find yourself standing up an HTTP server, something has gone wrong")
- **Unlocks:** S-01, S-02, S-03 — none of them have anywhere to attach a user-invokable command without this
- **Prerequisites:** —
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Mechanical scaffold work with a direction already dictated by `tech-stack.md`; low risk. Sequenced first because every vertical slice needs a command to invoke.
- **Status:** ready

## Slices

### S-01: User can see reconstructed rows with OCR confidence flagged

- **Outcome:** user points the tool at a scanned debtor-list image (one supported layout) and sees the reconstructed table rows, with low-confidence OCR fragments flagged rather than silently trusted.
- **Change ID:** scan-row-reconstruction
- **PRD refs:** FR-001, FR-002, FR-003, US-01, NFR (temporary artifacts cleaned up once the request completes)
- **Prerequisites:** F-01
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:**
  - Do we have a real representative distorted (wavy/skewed) scan to build and validate row-reconstruction against, rather than a clean synthetic one? — Owner: user. Block: yes.
- **Risk:** This slice tests the core idea the whole project depends on — that table-row geometry can be resolved correctly even on a distorted scan. Sequenced immediately after F-01, before any search or redaction logic is built on top of row data that might turn out to be wrong on a real scan.
- **Status:** blocked

### S-02: User can search by name and confirm/preview the match

- **Outcome:** user searches the reconstructed rows with a single free-text name query, is required to confirm when more than one row matches, and sees a preview of the matched row before requesting output.
- **Change ID:** person-search-confirm
- **PRD refs:** FR-004, FR-005, FR-006, FR-007, US-01
- **Prerequisites:** S-01
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:**
  - Does exact-match search hold up against real OCR noise, or does even one misread character make exact-match-only unreliable (FR-005's own stated concern)? — Owner: user/team. Block: no — the search/confirm/preview flow can be planned and built structurally without a real scan; only its accuracy needs one to validate.
- **Risk:** Depends on S-01 producing usable rows; a wrong or missing row makes search meaningless. Sequenced right after S-01 so the guardrail against silent auto-pick on an ambiguous match (FR-006) lands before any redaction is possible.
- **Status:** proposed

### S-03: User can generate the person-selective redacted PDF

- **Outcome:** user requests the anonymized output and receives a new PDF in which the confirmed match's row is fully visible and every other row's data is permanently, unrecoverably redacted at the pixel level, while the original source image is left unmodified.
- **Change ID:** selective-redaction-output
- **PRD refs:** FR-008, FR-009, US-01, NFR (temporary artifacts cleaned up once the request completes)
- **Prerequisites:** S-02
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Carries the highest guardrail stakes — the overwrite is permanent and unrecoverable, and a wrong-but-confident row match here means genuinely exposing someone who should have stayed hidden. Sequenced last so redaction only ever runs against rows and matches already exercised by S-01 and S-02.
- **Status:** proposed

## Backlog Handoff

| Roadmap ID | Change ID                  | Suggested issue title                                                | Ready for `/10x-plan` | Notes |
| ---------- | --------------------------- | ---------------------------------------------------------------------- | ---------------------- | ----- |
| F-01       | cli-entrypoint-scaffold     | Scaffold CLI entrypoint (replace fastapi/uvicorn with Typer or Click) | yes                    | —     |
| S-01       | scan-row-reconstruction     | Reconstruct and preview table rows from a scanned debtor list          | no                     | Blocked on real-scan Unknown — see Open Roadmap Questions #1 |
| S-02       | person-search-confirm       | Search debtor rows by name with confirm + preview                     | no                     | Prerequisite S-01 not yet done |
| S-03       | selective-redaction-output  | Generate person-selective redacted PDF output                         | no                     | Prerequisite S-02 not yet done |

## Open Roadmap Questions

1. **Do we have a real representative distorted (wavy/skewed) scan to build and validate row-reconstruction against, rather than a clean synthetic one?** — Owner: user. Block: S-01 (blocking); also informs S-02's exact-match reliability design.
2. **Should the "basic audit log" (PRD's Secondary success criterion) be promoted to a functional requirement and become a roadmap slice, or is it explicitly out of MVP scope?** — Owner: user. Block: roadmap-wide — no slice currently traces to it, and it cannot become one without a PRD FR to back it (unlike the preview criterion, which was promoted to FR-007).

## Parked

- **Arbitrary document layouts** — Why parked: PRD Non-Goal; only the one representative layout is supported for v1, other formats are out of scope until this one is proven.
- **Handwritten documents** — Why parked: PRD Non-Goal; only printed/typed table content is supported, handwriting recognition is a materially different, harder problem.
- **Multi-user / roles** — Why parked: PRD Non-Goal; MVP is single-user, single-device with no auth or role separation (see Access Control).
- **PDF ingestion (render PDF pages → images, upload flow)** — Why parked: shape-notes' `Forward: technical-roadmap` and FR-001's Socrates note both name this as a deliberate MVP shortcut, not a dropped requirement — a fast-follow once the core search/redact loop (S-01 through S-03) is proven on image input.

## Done

