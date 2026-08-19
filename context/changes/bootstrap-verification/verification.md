---
bootstrapped_at: 2026-08-19T18:13:53Z
starter_id: fastapi
starter_name: FastAPI
project_name: cover-data
language_family: python
package_manager: uv
cwd_strategy: native-cwd
bootstrapper_confidence: first-class
phase_3_status: ok
audit_command: pip-audit
---

## Hand-off

```yaml
starter_id: fastapi
package_manager: uv
project_name: cover-data
hints:
  language_family: python
  team_size: solo
  deployment_target: self-host
  ci_provider: github-actions
  ci_default_flow: manual-promotion
  bootstrapper_confidence: first-class
  path_taken: custom
  quality_override: false
  self_check_answers:
    typed: true
    from_official_starter: true
    conventions: true
    docs_current: true
    can_judge_agent: true
  has_auth: false
  has_payments: false
  has_realtime: false
  has_ai: false
  has_background_jobs: false
```

### Why this stack

A solo developer shipping a 3-week after-hours redaction CLI whose hard parts are
OCR with per-fragment confidence, table-row reconstruction on distorted scans, and
pixel-permanent redaction into a PDF. Python wins on ecosystem for all three; the
registry carries no Python CLI card, so the `fastapi` card is used as the Python
vehicle — it is the only Python entry clearing all four agent-friendly gates
(`django` fails on explicit types) and it prescribes `uv`, which is the part that
actually matters for scaffolding. Its FastAPI and uvicorn dependencies are surplus
here and should be dropped for a CLI framework, since match confirmation and row
preview happen in the terminal plus an OS image viewer rather than a web UI.
Deployment is `self-host` because the tool runs on one caseworker's device and the
debtor PII it processes must not leave it; that same constraint rules out hosted
OCR APIs, so OCR stays local. CI runs lint and tests with manual promotion — there
is no server to deploy to.

## Pre-scaffold verification

| Signal       | Value   | Severity | Notes                                                                    |
| ------------ | ------- | -------- | ------------------------------------------------------------------------ |
| npm package  | not run | n/a      | non-JS starter; `cmd_template` invokes `uv`, not an npm-distributed CLI   |
| GitHub repo  | not run | n/a      | card `docs_url` is `https://fastapi.tiangolo.com`, not a github.com URL   |

No recency signal was available for this starter. Nothing to flag.

## Scaffold log

**Resolved invocation**: `uv init . && uv add fastapi uvicorn`
**Strategy**: native-cwd
**Exit code**: 0 (on second attempt; see environment note below)
**Pre-flight files-to-touch**: `pyproject.toml`, `main.py` / `src/`, `.python-version`, `README.md`, `.gitignore`
**Files written by CLI**: 4 tracked (`pyproject.toml`, `uv.lock`, `.python-version`, `src/cover_data/__init__.py`) plus an ignored `.venv/`
**Pre-existing files preserved**: `README.md`, `.gitignore` — both left byte-for-byte unchanged; uv did not overwrite or sideline them, so no `.scaffold` siblings were created

### Environment note — first attempt failed on TLS interception

The first run exited 2. `uv init .` succeeded; `uv add fastapi uvicorn` failed:

```
error: Failed to fetch: `https://pypi.org/simple/uvicorn/`
  Caused by: invalid peer certificate: UnknownIssuer
hint: Consider enabling use of system TLS certificates with the `--system-certs` command-line flag
```

This is a TLS-inspecting proxy on the network, not a packaging fault. Re-running as
`uv add --system-certs fastapi uvicorn` succeeded and installed 15 packages. This
environment needs `--system-certs` (or `UV_NATIVE_TLS=1`) for every uv network
operation; consider pinning it in `uv.toml` or the shell environment so it is not
rediscovered on each machine.

### Scaffold result

uv produced a packaged src-layout project rather than a flat `main.py`:

- `src/cover_data/__init__.py`
- `pyproject.toml` with `requires-python = ">=3.14"` and a console-script entry point `cover-data = "cover_data:main"`
- `uv.lock` (15 packages), `.python-version` pinned to 3.14

The console-script entry point is CLI-shaped, which suits this project. Note the
entry point references a `main` symbol that does not exist in `__init__.py` yet.

## Post-scaffold audit

**Tool**: `pip-audit`
**Status**: failed to run
**Reason**: the same TLS-interception proxy blocks pip-audit's vulnerability lookups. pip-audit installed and started cleanly via `uvx`, but it uses `requests`/`certifi` rather than the system certificate store, so `--system-certs` does not help it. Both vulnerability services were tried.

**Partial output (if any)**:

```
requests.exceptions.SSLError: HTTPSConnectionPool(host='pypi.org', port=443):
  Max retries exceeded with url: /pypi/boolean-py/5.0/json
  (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED]
  certificate verify failed: unable to get local issuer certificate')))

requests.exceptions.SSLError: HTTPSConnectionPool(host='api.osv.dev', port=443):
  Max retries exceeded with url: /v1/query
  (Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED]
  certificate verify failed: unable to get local issuer certificate')))
```

The 15 installed packages are therefore **unaudited**. To resolve, point requests at
the corporate root CA via `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE`, or run the audit
from an unproxied network. Audit findings are informational in this workflow, so the
run continued.

## Hints recorded but not acted on

| Hint                    | Value                                                             |
| ----------------------- | ----------------------------------------------------------------- |
| bootstrapper_confidence | first-class                                                       |
| quality_override        | false                                                             |
| path_taken              | custom                                                            |
| self_check_answers      | typed, from_official_starter, conventions, docs_current, can_judge_agent — all true |
| team_size               | solo                                                              |
| deployment_target       | self-host                                                         |
| ci_provider             | github-actions                                                    |
| ci_default_flow         | manual-promotion                                                  |
| has_auth                | false                                                             |
| has_payments            | false                                                             |
| has_realtime            | false                                                             |
| has_ai                  | false                                                             |
| has_background_jobs     | false                                                             |

## Next steps

Next: a future skill will set up agent context (CLAUDE.md, AGENTS.md). For now, your project is scaffolded and verified — happy hacking.

Note: `CLAUDE.md` and `AGENTS.md` already exist in this repo, written before this run.

Useful manual steps in the meantime:
- `git init` — already done; the repo has one commit (`init project`).
- No `.scaffold` siblings were created, so there is nothing to reconcile.
- Address audit findings per your project's risk tolerance — but see above: the audit could not run, so the dependency tree is currently unaudited.

Project-specific follow-ups this run surfaced:
- Drop `fastapi` and `uvicorn` (`uv remove fastapi uvicorn`) and add a CLI framework — the hand-off rationale calls both surplus. They were installed because the registry card's `cmd_template` prescribes them.
- Add the real dependencies: OCR, image/geometry, and PDF libraries, plus `ruff`, `mypy`, and `pytest` as dev dependencies — `lefthook.yml` already invokes all three.
- Define `main` in `src/cover_data/__init__.py`, or repoint the `cover-data` console script.
- Fill in `description` in `pyproject.toml` (currently the uv placeholder).
