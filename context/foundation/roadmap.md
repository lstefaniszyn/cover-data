---
project: "Cover the Data"
version: 1
status: draft
created: 2026-08-19
updated: 2026-08-20
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
| F-01 | cli-entrypoint-scaffold    | (foundation) invoke the tool as a real CLI command instead of a stub                     | —              | tech-stack.md CLI decision   | done    |
| S-01 | scan-row-reconstruction    | point the tool at a scanned image and see reconstructed rows with OCR confidence flagged | F-01           | FR-001, FR-002, FR-003, US-01, NFR | ready   |
| S-02 | person-search-confirm      | search rows by name and confirm/preview the matched row before proceeding                | S-01           | FR-004, FR-005, FR-006, FR-007, US-01 | proposed |
| S-03 | selective-redaction-output | generate an output PDF where the confirmed match stays visible and every other row is permanently redacted, source untouched | S-02 | FR-008, FR-009, US-01, NFR | proposed |

## Baseline

What's already in place in the codebase as of `2026-08-20` (auto-researched + user-confirmed).
Foundations below assume these are present and do NOT re-scaffold them.

- **Frontend/interface:** present as of F-01 — Typer wired in `src/cover_data/cli.py` with `inspect`, `search` and `redact` registered as stubs; `main()` only calls `app()`. The project deliberately uses terminal + OS image viewer as its interface (per `tech-stack.md`), not a web UI.
- **Backend / core logic:** absent — no OCR, row-reconstruction, search, or redaction code exists yet; the three subcommands are stubs that exit 1.
- **Data:** absent by design — the PRD needs no database (single-user, file-in/file-out); no ORM/DB driver in dependencies.
- **Auth:** absent by design — PRD Access Control and `tech-stack.md` both specify single-user, no auth layer for MVP.
- **Deploy / infra:** present — `.github/workflows/ci.yml` (lint/test/typecheck) and `release.yml` (PyInstaller Windows `.exe` on tag push); `lefthook.yml` mirrors CI locally; self-host deploy target declared.
- **Observability:** absent — no logging library; the PRD's "basic audit log" is a Secondary success criterion only, never promoted to a functional requirement (see Open Roadmap Questions).
- **Test fixtures:** present as of `2026-08-20` — six synthetic sample scans at `context/test_images/` forming a distortion ladder (tilt, lighting, waviness, blur/noise, cut-off columns, artifacts), eight debtor rows each, placeholder names rather than real personal data. Enough to build against; not enough to validate FR-003/FR-005 (see Open Roadmap Questions #1). No hand-labelled ground truth yet — that is `context/foundation/test-plan.md` §3 Phase 1.
- **Test strategy:** present — `context/foundation/test-plan.md` (written `2026-08-20`) carries a seven-risk map and a five-phase test rollout. Its Phase 2 maps onto S-01; its Phase 4 onto S-02 and S-03.

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
- **Status:** done — `fastapi`/`uvicorn` removed, Typer wired, `inspect`/`search`/`redact` registered as stubs in `src/cover_data/cli.py`, `main()` reduced to calling `app()`. All plan phases and the manual verification checklist are complete (`context/changes/cli-entrypoint-scaffold/plan.md`, verified `2026-08-20`). Change folder not yet archived — run `/10x-archive cli-entrypoint-scaffold`.

## Slices

### S-01: User can see reconstructed rows with OCR confidence flagged

- **Outcome:** user points the tool at a scanned debtor-list image (one supported layout) and sees the reconstructed table rows, with low-confidence OCR fragments flagged rather than silently trusted.
- **Change ID:** scan-row-reconstruction
- **PRD refs:** FR-001, FR-002, FR-003, US-01, NFR (temporary artifacts cleaned up once the request completes)
- **Prerequisites:** F-01
- **Parallel with:** —
- **Blockers:** —
- **Fixtures:** six synthetic sample scans at `context/test_images/` (`1.png`–`6.png`, committed in `3f451c5`) — a distortion ladder covering tilt (`1.png`), lighting and shadows (`2.png`), page waviness (`3.png`), blur and noise (`4.png`), columns cut off at the page edge (`5.png`), and scan lines/artifacts (`6.png`); eight debtor rows each, placeholder names rather than real personal data. Each page is titled "Przykład N"; prefer an explicit fixture manifest over filename-derived identity.
- **Unknowns:**
  - What does "the one supported layout" mean, given the samples contain three variants? — Owner: user. Block: **no** for starting the slice; **yes** for hand-labelling ground truth. A (`Lp.` + split name, 6 cols): `1.png`, `3.png`. B (`Lp.` + merged name, 5 cols): `2.png`, `4.png`, `6.png`. C (no `Lp.`, split name, 5 cols): `5.png`. Either a fixed column schema is chosen — noting that B discards both the waviness and cut-off-column samples — or "one layout" is read as a family of bordered debtor tables with per-document column detection, keeping all six in scope. "Correct row reconstruction" is undefined until this is settled. See PRD Open Question #2.
  - Will a real representative distorted scan be available to validate against? — Owner: user. Block: **no**. The synthetic set is enough to build and exercise against, but not to prove FR-003 or FR-005 — its waviness case is mild, and it is exactly the clean synthetic set the original question warned about. See PRD Open Question #1.
- **Risk:** This slice tests the core idea the whole project depends on — that table-row geometry can be resolved correctly even on a distorted scan. Sequenced immediately after F-01, before any search or redaction logic is built on top of row data that might turn out to be wrong on a real scan. Now unblocked for *building*, but shipping it as proven still depends on the residual real-scan question above — treat a green suite against the synthetic ladder as necessary, not sufficient.
- **Status:** ready

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
| F-01       | cli-entrypoint-scaffold     | Scaffold CLI entrypoint (replace fastapi/uvicorn with Typer or Click) | done                   | Shipped; change folder pending `/10x-archive` |
| S-01       | scan-row-reconstruction     | Reconstruct and preview table rows from a scanned debtor list          | yes                    | Unblocked `2026-08-20` — sample scans available at `context/test_images/`. Settle the layout question (PRD Open Question #2) during planning; real-scan validation remains outstanding |
| S-02       | person-search-confirm       | Search debtor rows by name with confirm + preview                     | no                     | Prerequisite S-01 not yet done |
| S-03       | selective-redaction-output  | Generate person-selective redacted PDF output                         | no                     | Prerequisite S-02 not yet done |

## Open Roadmap Questions

1. **Partially resolved `2026-08-20` — no longer blocks S-01.** Six synthetic sample scans exist at `context/test_images/`, enough to build and exercise row reconstruction against. They do not validate it: the set is the clean synthetic one this question warned about, and its waviness case is mild. **Residual** — Owner: user: can a real representative distorted scan be obtained before FR-003 and FR-005 are treated as proven? Block: none for building; blocks calling S-01 *done with confidence*, and still informs S-02's exact-match reliability design.

2. **What does "the one supported layout" mean, given `context/test_images/` contains three variants?** — Owner: user. A (`Lp.` + split name, 6 cols): `1.png`, `3.png`. B (`Lp.` + merged name, 5 cols): `2.png`, `4.png`, `6.png`. C (no `Lp.`, split name, 5 cols): `5.png`. Either one variant is chosen as a fixed column schema and the rest become out-of-scope negatives — noting B discards both the waviness and cut-off-column samples — or "one layout" is read as a family of bordered debtor tables with per-document column detection. Block: S-01's ground-truth labelling (not its start). See PRD Open Question #2 and `context/foundation/test-plan.md` §2 "Fixture set".
3. **Should the "basic audit log" (PRD's Secondary success criterion) be promoted to a functional requirement and become a roadmap slice, or is it explicitly out of MVP scope?** — Owner: user. Block: roadmap-wide — no slice currently traces to it, and it cannot become one without a PRD FR to back it (unlike the preview criterion, which was promoted to FR-007).

## Parked

- **Arbitrary document layouts** — Why parked: PRD Non-Goal; only the one representative layout is supported for v1, other formats are out of scope until this one is proven.
- **Handwritten documents** — Why parked: PRD Non-Goal; only printed/typed table content is supported, handwriting recognition is a materially different, harder problem.
- **Multi-user / roles** — Why parked: PRD Non-Goal; MVP is single-user, single-device with no auth or role separation (see Access Control).
- **PDF ingestion (render PDF pages → images, upload flow)** — Why parked: shape-notes' `Forward: technical-roadmap` and FR-001's Socrates note both name this as a deliberate MVP shortcut, not a dropped requirement — a fast-follow once the core search/redact loop (S-01 through S-03) is proven on image input.

## Done

- **F-01: CLI entrypoint scaffold** (`cli-entrypoint-scaffold`) — completed `2026-08-20`. Surplus `fastapi`/`uvicorn` removed, Typer wired as the entrypoint, `inspect`/`search`/`redact` registered as stubs pointing at S-01/S-02/S-03, `[tool.mypy] strict` configured, and `CLAUDE.md` given its "CLI framework" and "Typing discipline" conventions. Plan fully closed including the manual verification checklist. Change folder pending `/10x-archive cli-entrypoint-scaffold`.

