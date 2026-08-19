---
project: cover-data
checked_at: 2026-08-19T00:00:00Z
health_status: needs-attention
context_type: brownfield
language_family: python
stack_assessment_available: true
checks_run:
  - lockfile
  - dependency_audit
  - outdated_deps
  - test_runner
  - ci_cd
  - configuration
audit_findings:
  critical: 0
  high: 0
  moderate: 0
  low: 0
test_runner_detected: true
ci_provider: GitHub Actions
recommended_fixes: 6
---

## Dependency Health

### Lockfile

```
Status: present (uv.lock)
Package manager: uv
```

`uv lock --check` confirms the lockfile matches `pyproject.toml` — no drift. 26 packages resolved (8 direct: `fastapi`, `uvicorn` runtime; `mypy`, `pytest`, `ruff` dev group; the rest transitive).

### Security Audit

```
Tool: uv run --with pip-audit pip-audit --format json
Status: failed to run
Reason: SSL: CERTIFICATE_VERIFY_FAILED — pip-audit's own HTTP client (requests/certifi via urllib3) cannot verify pypi.org's certificate through this network's TLS-inspecting proxy.
```

This is not a clean bill of health — it's an unaudited dependency tree. `pip-audit` uses `requests`/`certifi` rather than the system certificate store, so `uv`'s own `--system-certs` flag (which fixes this for `uv sync`/`uv run` itself) doesn't propagate to pip-audit's internal HTTP calls once it's running as the target tool. `CLAUDE.md` already documents this exact limitation. The 0/0/0/0 audit-findings count above reflects "never completed," not "verified clean."

**Important distinction not yet captured anywhere in the repo**: this proxy is a *local network* constraint. GitHub Actions runners are not behind it, so a `pip-audit` (or `uv`-native audit) step added to `ci.yml` would very plausibly succeed there even though it fails on this machine — see Recommended Fixes.

#### Direct vs transitive

Not assessed (audit didn't complete). `uv tree` shows the full dependency graph is shallow — `fastapi` and `uvicorn` pull in `pydantic`, `starlette`, `anyio`, `h11`, `click`; removing the two surplus runtime deps (see Recommended Fixes) would shrink the audit surface by roughly two-thirds of the current tree before any audit tool needs to run.

### Outdated Dependencies

```
Packages with major version gaps: 0
```

`uv pip list --outdated` shows one package one minor version behind: `pydantic-core` 2.46.4 → 2.48.0. No major-version gaps among the 8 direct dependencies. Not flagged as a fix item — this is routine drift, not a risk.

## Test Suite

```
Test runner: pytest 9.1.1
Tests found: 1 test
Test execution: passing
```

```
Configuration: pyproject.toml [tool.pytest.ini_options] (testpaths = ["tests"], custom "slow" marker registered)
Framework: pytest 9.1.1
```

`pytest --collect-only` cleanly collects `tests/test_smoke.py::test_package_is_importable`, and it passes. Coverage is minimal by design — the smoke test only guards that the src-layout package imports; the test file's own docstring says real coverage arrives with the first roadmap slice. Not a finding at this stage, since no feature code exists yet to test.

## CI/CD

```
Provider: GitHub Actions
Configuration: .github/workflows/ci.yml, .github/workflows/release.yml
```

| Stage      | Status | Notes                                                        |
|------------|--------|---------------------------------------------------------------|
| Lint       | ✓      | `ruff check .` + `ruff format --check .` (ci.yml)             |
| Test       | ✓      | `pytest` via `uv run --locked` (ci.yml)                       |
| Build      | ~      | No plain build/package step in `ci.yml`; PyInstaller build exists but only runs in `release.yml` on tag push |
| Type check | ✓      | `mypy src` via `uv run --locked` (ci.yml) — but see the mypy config gap below; the step runs, just weakly |
| Security   | ✗      | No dependency-audit step, no Dependabot config, no CodeQL workflow |

`ci.yml` and `release.yml` both mirror `lefthook.yml`'s local gate exactly (format-check → lint → lockfile-check → test → typecheck), which is good discipline — no drift between what a contributor runs locally and what CI enforces. The one asymmetry is the missing security-scan stage, addressed below.

## Configuration

### Medium severity

- **`[tool.mypy]` section** — absent from `pyproject.toml`. mypy runs on every commit and in CI but under default (permissive) settings, so it won't catch missing return types on internals or `Any`-typed data structures. Fix: add a `[tool.mypy]` section with `strict = true`, `files = ["src"]`.
- **Stack-assessment's recommended instruction-file entries** — `context/foundation/stack-assessment.md` (from the prior `/10x-stack-assess` run) drafted two ready-to-paste `CLAUDE.md` sections ("CLI framework" convention and "Typing discipline"). Neither has been added yet — `CLAUDE.md` still only mentions Typer in passing (as an example in the `.mcp.json` paragraph), not as a documented convention. Fix: paste both blocks from `stack-assessment.md`'s "Recommended Instruction File Additions" section into `CLAUDE.md`.

### Low severity

- **`.editorconfig`** — absent. Low impact for a single-contributor project, but cheap to add. Fix: add a minimal `.editorconfig` (`indent_style = space`, `indent_size = 4`, `charset = utf-8`, `end_of_line = lf`, `insert_final_newline = true`) — the project has no auto-formatting disagreement risk today (single contributor), so this is convenience, not urgency.

No other configuration gaps: `.gitignore` already covers Python artifacts correctly (`__pycache__/`, `.venv`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`) despite `CLAUDE.md`'s warning that it was inherited from a Backstage monorepo — someone has already patched it. `.env` is correctly excluded from git and not tracked. `.env.example` exists (documents MCP tool keys, not project runtime config — there is no project-level env var surface yet).

## Stack Assessment Cross-Reference

```
Stack assessment: context/foundation/stack-assessment.md
Agent readiness (from stack-assess): ready-with-compensation
```

| Quality Gate Gap                          | Health-Check Finding                                                                 | Status     |
|--------------------------------------------|----------------------------------------------------------------------------------------|------------|
| Framework: fail (no CLI framework chosen)  | `fastapi`/`uvicorn` still present as runtime deps; no Typer/Click in the dependency tree; CI has no framework-specific checks either | Reinforced |
| Typed: pass-with-note (mypy unconfigured)  | Confirmed — no `[tool.mypy]` section in `pyproject.toml`; CI's typecheck step runs, but weakly | Reinforced |
| Compensation: recommended CLAUDE.md entries | Neither recommended block (CLI framework convention, typing discipline) has been added yet | Gap — compensation drafted but not applied |

Both gaps stack-assess identified are still open, and the compensation it already wrote out hasn't been applied to the instruction files yet — the fix is drafted, just not pasted in.

## Recommended Fixes

### Fix before agent work (Category A)

### 1. Dependency tree is unaudited

**Impact**: an agent (or you) cannot currently verify there's no known CVE in `fastapi`, `uvicorn`, `starlette`, or their transitive deps before writing code against them.
**Severity**: high (unknown state, not a confirmed vulnerability)
**Effort**: quick (CI fix) + moderate (local workaround)
**Fix**:
- Add a security step to `ci.yml` — GitHub-hosted runners aren't behind this network's proxy, so it should succeed there even though it fails locally:
  ```yaml
  - name: Security audit
    run: uv run --with pip-audit pip-audit --format json
  ```
- For local ad-hoc audits, point `pip-audit`'s `requests` session at the proxy's CA bundle instead of relying on `--system-certs` (which only covers `uv`'s own HTTP calls): export the proxy's root certificate and set `REQUESTS_CA_BUNDLE=/path/to/proxy-ca.pem` before running `uv run --with pip-audit pip-audit`. Document the resolved path in `CLAUDE.md` once found so future sessions don't rediscover this.

### 2. No CLI framework selected; surplus `fastapi`/`uvicorn` still installed

**Impact**: every agent session touching `src/cover_data/__init__.py` risks inventing a different command-registration pattern than the last one, since there's no convention to anchor to yet — this is the Framework gate gap `stack-assessment.md` already identified.
**Severity**: medium
**Effort**: moderate
**Fix**:
```bash
uv remove fastapi uvicorn
uv add typer
```
Then split `main()` out of `src/cover_data/__init__.py` into a `src/cover_data/cli.py` with a `typer.Typer()` app, per the convention block already drafted in `context/foundation/stack-assessment.md`.

### 3. mypy has no strict configuration

**Impact**: the typecheck gate that runs on every commit and in CI is weaker than it looks — it won't flag untyped internals or `Any`-typed OCR/row data structures, which is exactly where this project's core risk (holding OCR-fragment → cell → row → person relationships together correctly) would hide a silent bug.
**Severity**: medium
**Effort**: moderate (adding the config is quick; resolving whatever it newly flags may take longer)
**Fix**: add to `pyproject.toml`:
```toml
[tool.mypy]
strict = true
files = ["src"]
```

### 4. Stack-assessment's compensation entries aren't in CLAUDE.md yet

**Impact**: the compensation strategy for gaps 2 and 3 above already exists as ready-to-paste text in `context/foundation/stack-assessment.md`, but until it's actually in `CLAUDE.md`, an agent reading only the instruction file won't see it.
**Severity**: medium
**Effort**: quick
**Fix**: copy the two fenced blocks under `stack-assessment.md`'s "Recommended Instruction File Additions" heading into `CLAUDE.md`.

### 5. No security-scan stage in CI

**Impact**: same root cause as #1 — once the CI-side pip-audit step is added (see #1's first fix), this closes automatically. Listed separately because it's a CI-coverage gap on its own, not just a local audit gap.
**Severity**: medium
**Effort**: quick (folds into fix #1)
**Fix**: see #1.

### 6. No `.editorconfig`

**Impact**: minor — single-contributor project today, so no active formatting disagreement. Cheap insurance if a second contributor joins.
**Severity**: low
**Effort**: quick
**Fix**: add a minimal `.editorconfig` with `indent_style = space`, `indent_size = 4`, `charset = utf-8`, `end_of_line = lf`, `insert_final_newline = true`.

### Addressed in upcoming lessons (Category B)

None outstanding. Unusually for a project at this stage, CI/CD ([Sprint Zero z Agentem: infrastruktura, walking skeleton i pierwszy deploy (M1L5)](https://platforma.przeprogramowani.pl/external/10xdevs-3/m1-l5) territory), agent instruction files ([Agent Onboarding: Agents.md, AI Rules i feedback loops (M1L4)](https://platforma.przeprogramowani.pl/external/10xdevs-3/m1-l4) territory), and deployment configuration are all already in place — `ci.yml`/`release.yml`, `CLAUDE.md`/`AGENTS.md`, and the PyInstaller release pipeline exist and are wired up. The remaining work is refining what's there (Category A above), not standing it up from scratch.

## Summary

Health status: needs-attention

The project's operational bones are solid: a locked, drift-checked dependency tree, a working test runner, and CI that mirrors the local git-hook gate exactly, so nothing passes locally that would fail remotely (or vice versa). The gaps are concentrated and already half-diagnosed by the project's own docs — an unaudited dependency tree (blocked by a local network proxy that shouldn't affect CI), a still-pending CLI framework decision with surplus `fastapi`/`uvicorn` weight left over from the wrong project, and a typecheck gate that runs but isn't configured strictly enough for the data-integrity problem this tool exists to solve. None of these compound into something an agent can't work around — they're addressable in a single focused pass.

Next step: work through the Category A fixes above (start with adding the CI-side `pip-audit` step, since it's the cheapest and de-risks the rest), then proceed to `/10x-roadmap` — noting that this project's `CLAUDE.md` describes itself as being in the greenfield chain (`tech-stack-selector` ✅ → `bootstrapper` ✅ → `roadmap` next) even though `/10x-stack-assess` and `/10x-health-check` are documented as brownfield-chain tools. Running them here was still worthwhile as a post-bootstrap sanity check, but the canonical next step per the project's own stated flow is `/10x-roadmap`, not another brownfield-chain skill.
