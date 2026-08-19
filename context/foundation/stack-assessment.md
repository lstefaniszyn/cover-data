---
project: cover-data
assessed_at: 2026-08-19T00:00:00Z
agent_readiness: ready-with-compensation
context_type: brownfield
stack_components:
  language: Python 3.14
  framework: none (CLI framework not yet selected — fastapi/uvicorn present but flagged as surplus)
  build_tool: uv
  test_runner: pytest 9.1.1
  package_manager: uv
  ci_provider: GitHub Actions
  deployment_target: self-host (PyInstaller Windows .exe via GitHub Release)
gates_passed: 6
gates_failed: 3
---

## Stack Components

**Language**: Python 3.14 (`.python-version`, `requires-python = ">=3.14"` in `pyproject.toml`). Type hints are used in the one real source line (`src/cover_data/__init__.py`: `def main() -> None:`). `mypy>=2.3.1` is a dev dependency and is wired into both `lefthook.yml` (pre-commit and pre-push) and `.github/workflows/ci.yml`/`release.yml`, but `pyproject.toml` has no `[tool.mypy]` section, so it runs under mypy's default (permissive) settings rather than an explicit strict configuration.

**Framework**: none installed. `pyproject.toml` currently lists `fastapi` and `uvicorn` as runtime dependencies — both inherited from the `trade-with-me` scaffold this repo was copied from, and both already flagged as surplus in `CLAUDE.md` ("If you find yourself standing up an HTTP server, something has gone wrong"). The actual product is a single-command CLI (`cover-data = "cover_data:main"` console script in `pyproject.toml`), and no CLI framework (Typer, Click) is installed yet — `main()` is a bare one-line stub.

**Build tool**: uv, with `uv_build` as the PEP 517 backend (`[build-system]` in `pyproject.toml`) and `uv.lock` committed. `.python-version` pins the interpreter uv resolves. CI installs uv via `astral-sh/setup-uv@v5` and runs every command through `uv run --locked`, so a drifted lockfile fails loudly in CI rather than silently diverging from local runs.

**Test runner**: pytest 9.1.1, dev dependency, `testpaths = ["tests"]` configured in `[tool.pytest.ini_options]`, with a registered `slow` marker so `lefthook.yml`'s pre-commit hook can run a fast subset (`pytest -q -x -m 'not slow'`) while pre-push and CI run the full suite. One smoke test exists (`tests/test_smoke.py`), asserting only that the package imports.

**Package manager**: uv (`uv sync --locked`, `uv add`/`uv remove`).

**CI/CD**: GitHub Actions, two workflows. `ci.yml` runs format-check → lint → lockfile-check → test → typecheck on every push/PR to `main`, mirroring `lefthook.yml`'s pre-push gate exactly. `release.yml` triggers on `v*` tags or manual dispatch, re-runs the same gate, then packages a one-file Windows executable with PyInstaller and attaches it to a GitHub Release — appropriate for the self-host deployment target (a caseworker's machine, no server to deploy to).

**Instruction files**: `CLAUDE.md` (10KB, detailed — covers repo state, inherited cruft from the prior project, domain invariants, and the `context/` workflow) and `AGENTS.md` (3KB). Both already document the framework gap and prescribe the fix (drop fastapi/uvicorn, add Typer or Click).

## Quality Gate Assessment

| Component  | Typed | Convention | Training Data | Documented | Verdict    |
|------------|-------|------------|---------------|------------|------------|
| Language   | ✓     | —          | —             | —          | pass (~)   |
| Framework  | —     | ✗          | ✗             | ✗          | fail       |
| Build tool | —     | ✓          | ✓             | ✓          | pass       |
| Test runner| —     | —          | ✓             | ✓          | pass       |

Legend: ✓ = pass, ✗ = fail, ~ = partial, — = not applicable

### Gate Details

**Language — Typed: pass, with a caveat.** Python has no static types by default, but the project has mypy configured as a dev dependency and wired into every commit gate (`lefthook.yml` pre-commit `typecheck` job, `pre-push` `typecheck` job, and both `ci.yml`/`release.yml` `Typecheck` steps all run `uv run --locked mypy src`). Per the pass rule ("Python + mypy/pyright in deps/config"), this is a pass. The caveat: `pyproject.toml` has no `[tool.mypy]` section, so mypy runs under its default settings — it will not catch untyped function bodies, missing return types on internals, or `Any`-typed OCR/geometry data structures unless strict flags are turned on. Marked pass-with-note (`~`) rather than a clean pass.

**Framework — fail on all three applicable gates.** There is no CLI framework in the dependency tree. `fastapi`/`uvicorn` are present but are dead weight from the wrong project (`CLAUDE.md`'s own "Inherited cruft" table calls this out) and don't serve the actual product (a terminal CLI, not an HTTP service) — so they don't count as "the framework" for assessment purposes. With nothing installed: no folder/routing convention exists yet (convention-based: fail), there's nothing to be popular in training data (fail), and nothing to document (fail). Evidence: `pyproject.toml` dependencies list (`fastapi>=0.141.1`, `uvicorn>=0.52.4` only); `src/cover_data/__init__.py` is an 8-line stub with no command structure.

**Build tool — uv: pass on all three.** Convention: `pyproject.toml` + `uv.lock` + `src/` layout is uv's standard, opinionated project shape, reinforced everywhere (`lefthook.yml`, both workflow files, `CLAUDE.md`'s own command reference all assume `uv run` as the only entry point). Training data: uv is the ecosystem's fast-rising default for new Python projects and is well represented in recent training data, including as the `tech-stack.md` registry's own basis for `starter_id: fastapi`. Documented: `docs.astral.sh/uv` is versioned, current, and directly linkable — evidenced by the CI workflow using the officially documented `astral-sh/setup-uv@v5` action with the documented `.python-version` auto-detection behavior (explicitly called out in a `ci.yml` comment as the fix for a prior invalid input).

**Test runner — pytest: pass on both applicable gates.** Training data: pytest is the de facto standard Python test runner, heavily represented in training data. Documented: current, versioned, canonical docs at `docs.pytest.org`. Evidence: `[tool.pytest.ini_options]` in `pyproject.toml` uses documented pytest configuration (`testpaths`, custom `markers`) exactly as the official docs describe.

## Gaps & Compensation

### Gap 1: No CLI framework selected (Framework gate — fail on convention, training data, documented)

This is the one real gap, and it's already been diagnosed correctly in the repo's own docs (`CLAUDE.md` and `tech-stack.md` both flag it) — it just hasn't been acted on yet. Without a chosen framework, an agent writing the actual CLI commands has no folder convention to follow and will improvise argument parsing ad hoc, which is exactly the kind of drift the four gates exist to catch. The fix is narrow: pick Typer (recommended) or Click, both of which pass all four gates in their own right (typed via type-hint-driven parameter declarations, convention-based via decorator-registered commands, popular and well-documented within the Python CLI niche) — so this isn't a "live with the gap" situation, it's a "make the pending decision" situation.

**Why it matters for agent workflows**: until a framework is chosen, every agent session that touches `src/cover_data/__init__.py` risks inventing a different command-registration pattern than the last session did, since there's no convention to anchor to.

**Compensation strategy**: adopt Typer now, and document the resulting layout once real commands exist.

### Gap 2: mypy has no strict configuration (Typed gate — pass, but weakly)

`mypy` runs on every commit and in CI, but with no `[tool.mypy]` section it defaults to permissive checking — it won't flag an untyped internal function or a `dict`-typed OCR fragment where a proper model belongs. Given this project's core risk is exactly "holding OCR-fragment → cell → row → person relationships together correctly" (per `CLAUDE.md`'s domain invariants), loose typing on those data structures is where a silent bug would hide.

**Why it matters for agent workflows**: an agent extending row-reconstruction logic without a typed contract for what an OCR fragment or a row looks like is free to reinvent the shape each time, which is the same class of drift as Gap 1 but at the data-model level instead of the command-structure level.

**Compensation strategy**: tighten the mypy config and add a data-modeling convention to `CLAUDE.md`.

### Recommended Instruction File Additions

Ready-to-paste additions for `CLAUDE.md` (or `AGENTS.md`):

```markdown
## CLI framework

Commands are built with Typer, not bare `argparse` or a hand-rolled `sys.argv` parser.
- Each user-facing command is a function decorated with `@app.command()` in
  `src/cover_data/cli.py`; `src/cover_data/__init__.py`'s `main()` only calls
  `app()` — it holds no command logic itself.
- Command parameters use type hints (`Annotated[str, typer.Argument(...)]` /
  `typer.Option(...)`) — Typer derives validation and `--help` text from them,
  so an untyped parameter is a bug, not a style choice.
- Match-confirmation and row-preview prompts (see PRD FR-006, FR-007) go through
  Typer's `typer.confirm()` / `rich`-based output, not raw `input()`.
```

```markdown
## Typing discipline

`mypy` runs on every commit (`lefthook.yml`) and in CI (`ci.yml`, `release.yml`)
but currently has no `[tool.mypy]` section in `pyproject.toml`, so it checks
under default (permissive) settings. Add:

    [tool.mypy]
    strict = true
    files = ["src"]

OCR fragments, table rows, and person-match results are typed data structures
(Pydantic models or `@dataclass`, not raw `dict`s) — this is a domain invariant,
not a style preference: the hard problem in this project is keeping the
OCR-fragment → cell → row → person relationship correct under skewed/wavy scans
(see CLAUDE.md "Domain invariants"), and an untyped dict makes a shape mismatch
invisible until runtime.
```

## Summary

**Overall verdict: ready-with-compensation.** Three of four assessed components (language typing via mypy, uv as build tool, pytest as test runner) pass cleanly, and the CI/lefthook wiring around them is unusually disciplined for a 3-week solo project — the pre-commit/pre-push/CI gates all run the identical command sequence through `uv run --locked`, so there's no drift between what a contributor runs locally and what CI enforces.

**Key strength**: the tooling that exists is agent-friendly by construction — locked dependencies, a single package manager, gated commits, and instruction files that already correctly diagnose the project's own gaps (both `CLAUDE.md` and `tech-stack.md` independently flag the missing CLI framework before this assessment did).

**Key gap**: no CLI framework is installed yet. This isn't stack friction to route around — it's a pending decision the repo's own docs already point toward (Typer or Click), and it should be resolved before the first real command is written, not compensated for indefinitely. The secondary gap (unconfigured mypy) is cheap to close in the same pass.

**Recommended next step**: `/10x-health-check` — with this assessment as input, focus the health check on (1) whether `fastapi`/`uvicorn` get removed and a CLI framework added before the first roadmap slice lands, and (2) the currently-unaudited dependency tree (`CLAUDE.md` notes `pip-audit` can't be fixed for this network's TLS-inspecting proxy the way `uv` commands can).
