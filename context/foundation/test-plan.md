# Test Plan

> Phased test rollout for this project. Strategy is frozen at the top
> (§1–§5); cookbook patterns at the bottom (§6) fill in as phases ship.
> Read before writing any new test.
>
> Refresh: re-run `/10x-test-plan --refresh` when stale (see §8).
>
> Last updated: 2026-08-20

## 1. Strategy

Tests follow three non-negotiable principles for this project:

1. **Cost × signal.** The cheapest test that gives a real signal for the
   risk wins. Do not promote to e2e because e2e "feels safer." Do not put a
   vision model on top of a deterministic visual diff that already catches
   the regression.
2. **User concerns are first-class evidence.** Risks anchored in "the team
   is worried about X, and the failure would surface somewhere in `<area>`"
   carry the same weight as PRD lines or hot-spot data.
3. **Risks are scenarios, not code locations.** This plan documents *what
   could fail* and *why we believe it's likely* — drawn from documents,
   interview, and codebase *signal* (churn, structure, test base). It does
   NOT claim to know which line owns the failure. That knowledge is
   produced by `/10x-research` during each rollout phase. If the plan and
   research disagree about where the failure lives, research is the
   ground truth.

Hot-spot scope used for likelihood weighting: **none — scan skipped.** The
repository is 8 commits deep, all dated 2026-08-19, of which 3 touch
`src/`/`tests/` — below the 5-commit threshold for usable churn signal. The
scopes that would have been scanned are `src/` and `tests/`. Every
likelihood rating in §2 therefore rests on the Phase 2 interview, the PRD,
and the roadmap alone.

A fourth condition is specific to this project and worth stating plainly:
**most of the code under test does not exist yet.** Roadmap slice F-01
(CLI scaffold) has shipped; S-01, S-02 and S-03 have not. This plan is
therefore forward-looking — it pre-commits the oracle each upcoming slice
must be tested against, rather than backfilling coverage. That ordering is
deliberate: an oracle written before the implementation cannot be lifted
*from* the implementation, which is the failure mode most likely to make an
AI-written test green and worthless.

## 2. Risk Map

The top failure scenarios this project must protect against, ordered by
risk = impact × likelihood. Risks are failure scenarios in user / business
terms, not test names. The Source column cites the *evidence that surfaced
this risk* — never a specific file as "where the failure lives" (that is
research's job, see §1 principle #3).

| # | Risk (failure scenario) | Impact | Likelihood | Source (evidence — not anchor) |
|---|---|---|---|---|
| 1 | On a wavy or blurry scan the redaction band is misplaced against the true row boundary, leaving a strip of a **neighbouring** debtor's data visible in the output | High | High | interview Q1, Q2, Q3; PRD FR-003 and its Socrates note; roadmap S-01 risk note |
| 2 | The same misplacement in the opposite direction: the band over-reaches and **clips the target person's own row**, destroying the one row that had to stay fully visible | High | High | interview Q1; PRD US-01 acceptance criterion ("byte-for-byte visible… no accidental partial redaction"); PRD FR-008 |
| 3 | Debtor PII escapes the device through a channel that is not the output PDF — temp artifacts surviving a failed run, error output, or real-scan fixtures and CI logs | High | Medium | PRD Non-Functional Requirement (temp-artifact cleanup); `CLAUDE.md` domain invariant "PII must not leave the device"; interview clarifier (predecessor supplies no data, so hand-labelling is the only path). Downgraded from High likelihood on 2026-08-20 — see "Fixture set" below |
| 4 | A low-confidence OCR fragment flows downstream unflagged, and a wrong-but-confident name or row boundary is acted on | High | Medium-High | interview Q4; PRD FR-002 and its Socrates note |
| 5 | Redaction is a visual cover-up rather than a pixel overwrite — original content remains recoverable from the output PDF | High | Medium | PRD Guardrails; PRD FR-008; `CLAUDE.md` domain invariant "true redaction, never a visual cover-up" |
| 6 | A query matching more than one row produces output without explicit confirmation — silent auto-pick | High | Medium | PRD FR-006 and its Socrates note; PRD US-01 acceptance criterion |
| 7 | The source file is modified or overwritten by a run, including on the error path | High | Low-Medium | PRD FR-009 and its Socrates note; PRD US-01 acceptance criterion |

**Abuse / security lens.** The product has no authentication and no
payments, and runs single-user on one device, so the authorization/IDOR,
injection, and resource-abuse classes do not apply. The class that does
apply is **secret/PII leakage**, carried by Risk #3. Risk #3 is unusual and
deserves emphasis: this rollout is itself the most likely cause of it,
because hand-labelling real distorted scans necessarily puts real debtor
data into the working tree of a repository that has a remote.

### Fixture set (assessed 2026-08-20)

Six sample scans exist at `context/test_images/` — a deliberate distortion
ladder, one page each, eight debtor rows per page:

| File | Label | Distortion exercised | Column layout |
|---|---|---|---|
| `1.png` | Przykład 1 | clean, slightly tilted | 6 columns, given/family name split |
| `2.png` | Przykład 2 | shadows, uneven lighting | 5 columns, name merged |
| `3.png` | Przykład 3 | page waviness | 6 columns, given/family name split |
| `4.png` | Przykład 4 | low quality, blur and noise | 5 columns, name merged |
| `5.png` | Przykład 5 | columns cut off at the right edge | 5 columns, name merged, last column truncated |
| `7.png` | Przykład 6 | scan lines and artifacts | 5 columns, name merged |

Five findings, which the risk map above already reflects:

1. **The set is synthetic and carries no real PII** — placeholder names and
   generic addresses. It can be committed. This is why Risk #3's likelihood
   is downgraded to Medium: only its temp-artifact and error-output halves
   remain live, and Risk #3 now ranks below Risk #4 despite its row
   position (numbers are stable by schema rule and are not renumbered).
2. **The set does not close the PRD's blocking open question**, which asks
   for a *real* representative distorted scan "rather than a clean
   synthetic one." Risks #1 and #2 can be exercised against this set but
   cannot be *closed* by it.
3. **The column schema is not stable across the set.** Two files split
   given and family name into separate columns; four merge them. The PRD
   scopes v1 to one representative layout. Either the MVP layout is chosen
   and the remaining files become out-of-scope negatives, or the
   one-layout assumption is wrong. **This is a blocking decision for §3
   Phase 1** — it defines what correct row reconstruction means before any
   ground truth can be labelled.
4. **`7.png` is labelled "Przykład 6" and no `6.png` exists.** A harness
   that indexes fixtures by filename will mislabel that case. Fixture
   identity should come from an explicit manifest, not from the filename.
5. **`5.png` is the sharpest available test of Risks #1 and #2**, because
   its last column runs off the page edge: a band computed from detected
   *content* extent rather than *page* extent stops short and leaves
   truncated text exposed. Conversely the waviness in `3.png` is mild, so
   the core wavy-geometry risk is under-exercised by this set — a further
   argument for finding a real distorted scan (finding 2).

Risk #7 sits at Low-Medium likelihood and is retained rather than dropped
because the PRD makes it a distinct testable requirement (FR-009) precisely
on the grounds that "we only read the file" is not an implementation
guarantee. Its defence is also close to free (see §3 Phase 4), so the usual
argument for pushing a low-likelihood risk to observability instead of a
test does not apply here.

### Risk Response Guidance

| Risk | What would prove protection | Must challenge | Context `/10x-research` must ground | Likely cheapest layer | Anti-pattern to avoid |
|---|---|---|---|---|---|
| #1 | No fragment of any non-target person's data is legible or extractable from the output, including the top and bottom pixel-rows of the band where ink bleed lives | "The correct row was *found*, so the band is *right*" — row index is not row extent. Also "the target's name is visible, therefore correct", an assertion that passes while a neighbour's surname sits exposed at the band edge | How row extent is computed and in which coordinate space; whether any deskew or rotation happens between OCR and redaction; what padding rule is applied | Integration test over hand-labelled real-scan fixtures | **Oracle lifted from the implementation** — expected row extents computed by calling the row-reconstruction code. Extents must be labelled independently of the code under test |
| #2 | The target person's row is pixel-identical to the source in the output | "A bigger safety margin is always safer" — over-padding to defend #1 directly causes #2 | Whether the output path re-encodes or recompresses the raster; a lossy re-encode changes the oracle from pixel identity to a tolerance comparison | The same test as #1, asserting the complementary region | Separate tests for #1 and #2 that can each be made green in isolation — the fix for one then silently breaks the other |
| #3 | After any run — success, failure, or interrupt — no file containing debtor data remains outside the declared output path, and none appears in stderr or logs; and the repository and CI artifacts never carry a real scan | "A `finally` block is enough" — it is not, for an interrupt signal, nor for an exception raised before the temp path is registered. Also "it is only a test fixture, it does not count" | Where temp artifacts are created; whether the OCR engine writes intermediates to disk of its own accord; what the error path prints | Integration test with an injected failure, plus a repository and CI gate | Testing only happy-path cleanup; committing a real scan "temporarily" |
| #4 | A fragment below the confidence threshold is visibly surfaced to the user, and is never silently used as the basis of a match or a row boundary | "Confidence is stored, therefore it is handled" — retaining the number in a typed structure is not flagging it | The confidence scale the chosen engine emits; where the threshold lives; how a flag propagates fragment → row → match; what the user actually sees | Unit tests on the flagging logic with synthetic fragments (no scan required), plus one assertion at the CLI boundary | Testing the OCR engine's own accuracy — explicit negative space, see §7. Asserting against a threshold constant copied out of the source |
| #5 | Content beneath a redaction is unrecoverable by text extraction, by embedded-image extraction, **and** by pixel inspection | "It looks black in the viewer" — a scanned page wrapped into a PDF can render black while the original intact image object remains extractable from the file | How the output PDF is assembled: is the redacted raster re-embedded as a new image, or is a rectangle drawn over the original image object? | Deterministic file-level assertions on the output PDF | Layering a vision model or screenshot diff over an extraction check that already answers the question definitively |
| #6 | When the query matches more than one row, no output artifact exists on disk unless the user explicitly confirmed | "One match in the fixture, therefore the path is covered" — the guardrail only fires on the multi-match path, which a happy-path fixture never exercises. Also, any future non-interactive or `--yes` flag as a silent bypass | How the match set is produced; where confirmation is requested; whether output-writing is reachable on any path that skips confirmation | CLI-level test driving both the confirm and the decline branch with simulated input | Asserting that the prompt text appeared, instead of asserting that declining produced no file |
| #7 | The source file's bytes and mtime are unchanged after success, after failure, and after interrupt | "We only open it for reading" — image libraries offer in-place operations, and a bug in deriving the output path from the input path targets the source | Every open of the source path and its mode; whether any library mutates in place; how the output path is derived from the input path | Hash-based check at unit level — very cheap | Checking only after a successful run; checking mtime alone |

## 3. Phased Rollout

Each row is a discrete rollout phase that will open its own change folder
via `/10x-new`. Status moves left-to-right through the values below; the
orchestrator updates Status as artifacts appear on disk.

| # | Phase name | Goal (one line) | Risks covered | Test types | Status | Change folder |
|---|---|---|---|---|---|---|
| 1 | Fixture foundation | Settle the one-layout question, then hand-label row-extent ground truth over `context/test_images/` and keep the door shut for real scans arriving later | #3 | fixture manifest + labelling, repo + CI gate, cleanup integration | change opened | `context/changes/testing-fixture-foundation/` |
| 2 | Row-extent ground truth | Prove the redaction band matches the true row boundary on both edges simultaneously, on real distorted scans | #1, #2 | integration over fixtures, `slow`-marked | not started | — |
| 3 | Confidence-flag propagation | Prove sub-threshold OCR fragments are surfaced and never silently used as the basis of a match or boundary | #4 | unit on synthetic fragments, one CLI-boundary assertion | not started | — |
| 4 | Guardrail suite | Prove true pixel overwrite, no silent auto-pick, and source immutability, including on failure paths | #5, #6, #7 | file-level output assertions, CLI tests with simulated input, hash checks | not started | — |
| 5 | Quality gates | Lock the floor in CI: close the open dependency-audit gap, keep the commit gate fast as fixture tests grow, make the full suite the release gate | cross-cutting | gates | not started | — |

Phase ordering rationale, one line each:

- **Phase 1 first** because nothing later can be tested honestly without
  independent ground truth, labelling cannot start until the one-layout
  question is settled (see "Fixture set" in §2, finding 3), and it is the
  only phase whose cost is dominated by human labelling rather than code.
- **Phase 2 second** because #1 and #2 are the highest impact × likelihood
  pair, three interview answers converge on them, and they test the
  assumption the entire product rests on. Maps to roadmap slice S-01
  (`scan-row-reconstruction`).
- **Phase 3 third** because it is the cheapest phase and needs no fixtures,
  but the confidence flag must propagate through row and match structures
  that do not exist until S-01 lands.
- **Phase 4 fourth** because its assertions are deterministic and largely
  independent of scan quality, so they can run against a small clean
  fixture — but they target roadmap slices S-02 and S-03, which are not
  built yet.
- **Phase 5 last** because gates lock in what the earlier phases
  established, and locking a floor before it exists produces a red build
  rather than a guarantee.

**Status vocabulary** (fixed — parser literals): `not started`,
`change opened`, `researched`, `planned`, `implementing`, `complete`.

## 4. Stack

The classic test base for this project. AI-native tools (if any) carry a
`checked:` date so future readers can see which lines need re-verification.

| Layer | Tool | Version | Notes |
|---|---|---|---|
| unit + integration | pytest | 9.1.1 | Configured in `pyproject.toml`; `testpaths = ["tests"]`; a `slow` marker is already registered for fixture-heavy OCR and full-page redaction tests, and the pre-commit gate filters it out |
| CLI invocation | `typer.testing.CliRunner` | Typer 0.27.1 | Already in use. Simulated stdin is the supported way to drive `typer.confirm` / `typer.prompt`, which is what Risk #6 needs |
| type checking | mypy (strict) | 2.3.1 | `strict = true`, `files = ["src"]`. Load-bearing rather than cosmetic here: the OCR-fragment → cell → row → person relationship is the project's core invariant, and an untyped dict hides a shape mismatch until runtime |
| lint + format | ruff | 0.16.3 | Vendored agent tooling excluded via `extend-exclude` |
| scan fixtures | six synthetic PNGs at `context/test_images/` | — | A distortion ladder (tilt, lighting, waviness, blur/noise, cut-off columns, artifacts), 8 rows each, no real PII. Untracked as of 2026-08-20. See "Fixture set" in §2 for the layout-instability and filename findings |
| ground-truth labelling | none yet — see §3 Phase 1 | — | The predecessor program supplies no data (not runnable, no saved output), so expected row extents must be hand-labelled — roughly 48 row bands across the six fixtures. This is the rollout's most expensive and most load-bearing asset |
| image + PDF assertions | none yet — see §3 Phase 2 and Phase 4 | — | PyMuPDF exposes page-level text extraction, embedded-image enumeration, and pixmap rendering — three independent deterministic oracles for Risk #5, so no vision model is warranted. Library choice is not yet committed; confirm during Phase 2 research |
| OCR engine | none yet — see roadmap S-01 | — | Must be local: `tech-stack.md` records an explicit avoid on hosted OCR APIs because debtor PII must not leave the device |
| dependency audit | none yet — see §3 Phase 5 | — | `pip-audit` fails on this network's TLS-inspecting proxy because it uses its own HTTP client rather than the system trust store; GitHub-hosted runners are not behind that proxy, so the gate belongs in CI |
| e2e / browser | not applicable | — | This is a CLI. A browser automation layer would add cost and no signal |

**Stack grounding tools (current session):**

- Docs: **Context7** — verified Typer's testing surface (simulated stdin via the test runner is the supported path for confirm/prompt flows) and PyMuPDF's extraction and rendering surface (page text extraction, embedded-image enumeration, pixmap rendering) as candidate oracles for Risk #5; checked: 2026-08-20
- Search: **Exa** — available, not used; local manifests and the PRD carried enough evidence; checked: 2026-08-20
- Runtime/browser: **Playwright / browser MCP** — available, not used; the product has no browser surface; checked: 2026-08-20
- Provider/platform: **GitHub** (via `gh` and GitHub Actions) — relevant only to §3 Phase 5, where the dependency-audit gate lands; checked: 2026-08-20

## 5. Quality Gates

The full set of gates that must pass before a change reaches production.
"Required after §3 Phase N" means the gate is enforced once that rollout
phase lands; before that, the gate is planned.

| Gate | Where | Required? | Catches |
|---|---|---|---|
| format check + lint | local (lefthook) + CI | required (wired) | style and syntactic drift |
| type check, strict | local (lefthook) + CI | required (wired) | untyped or `Any`-shaped OCR / row / match structures |
| lockfile check | local (lefthook) + CI | required (wired) | dependency drift between local and CI |
| unit + integration | local (lefthook) + CI | required (wired; meaningful after §3 Phase 2) | logic regressions |
| no real scan staged | local (lefthook) + CI | required after §3 Phase 1 | debtor PII entering git history |
| temp-artifact cleanup on failure | CI | required after §3 Phase 1 | PII surviving a crashed run |
| row-extent two-sided assertion | CI on PR | required after §3 Phase 2 | Risks #1 and #2 — the band drifting off either edge |
| output-recoverability assertion | CI on PR | required after §3 Phase 4 | Risk #5 — a cover-up shipped as a redaction |
| source-immutability assertion | CI on PR | required after §3 Phase 4 | Risk #7 — the only original being modified |
| dependency audit | CI | required after §3 Phase 5 | known CVEs in the dependency tree, currently unaudited |
| full suite including `slow` | local (pre-push) + release | required after §3 Phase 5 | fixture-heavy regressions escaping the fast commit gate |

## 6. Cookbook Patterns

How to add new tests in this project. Each sub-section is filled in once
the relevant rollout phase ships; before that, the sub-section reads
"TBD — see §3 Phase N."

### 6.1 Adding a scan fixture with labelled ground truth

- TBD — see §3 Phase 1. Will cover where real scans live versus what is
  committed, how expected row extents are hand-labelled, and the rule that
  a labelled extent is never produced by the code it will be used to test.

### 6.2 Adding a row-geometry test

- TBD — see §3 Phase 2. Will cover the two-sided assertion pattern for the
  redaction band: neighbouring rows fully destroyed and the target row
  fully intact, asserted together so neither can be satisfied by loosening
  the other.

### 6.3 Adding an OCR-confidence test

- TBD — see §3 Phase 3. Will cover constructing synthetic fragments at
  chosen confidence levels without needing a scan, and asserting that a
  flag reaches the user rather than merely being stored.

### 6.4 Adding an output-artifact assertion

- TBD — see §3 Phase 4. Will cover asserting on the produced file rather
  than on terminal output: unrecoverability by text extraction, by
  embedded-image extraction, and by pixel inspection.

### 6.5 Adding a CLI confirmation-flow test

- TBD — see §3 Phase 4. Will cover driving confirm and decline branches
  with simulated stdin, and asserting on filesystem state rather than on
  the prompt text.

### 6.6 Per-rollout-phase notes

(Filled in as phases land — two or three lines each, capturing anything
surprising the phase taught.)

## 7. What We Deliberately Don't Test

Exclusions agreed during the rollout (Phase 2 interview, Q5). Future
contributors should respect these unless the underlying assumption changes.

- **Raw OCR character accuracy of the engine itself** — the engine is not
  ours to fix; the only thing we control is whether we flag what it is
  unsure about. Re-evaluate if the project ever ships its own recognition
  model or a post-correction layer. (Source: Phase 2 interview Q5.)
- **Typer's own argument parsing and `--help` rendering** — covered by the
  framework's suite; asserting on it here churns without catching product
  defects. The existing scaffold tests that touch `--help` are wiring
  smoke, not a pattern to extend. Re-evaluate if the CLI grows dynamic
  command registration.
- **Differential comparison against the predecessor program** — considered
  and dropped: it is not runnable and no saved output exists, so a plan
  built on it would rest on data that does not exist. Re-evaluate if the
  program or its JSON findings ever become available. (Source: Phase 2
  interview clarifier.)

## 8. Freshness Ledger

- Strategy (§1–§5) last reviewed: 2026-08-20
- Stack versions last verified: 2026-08-20
- AI-native tool references last verified: 2026-08-20 (none adopted; see §4)

Refresh (`/10x-test-plan --refresh`) when:

- a new top-3 risk surfaces from the roadmap or archive,
- a recommended tool's `checked:` date is older than three months,
- the project's tech stack changes (new framework, new test runner, an OCR
  or PDF library committed),
- §7 negative-space no longer matches what the team believes,
- the hot-spot scan becomes viable — once the repository carries more than
  five commits of hand-written churn over thirty days, likelihood ratings
  in §2 should be re-weighted against real churn rather than interview
  evidence alone.
