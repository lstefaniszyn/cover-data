# CLI Entrypoint Scaffold Implementation Plan

## Overview

Replace the inherited `fastapi`/`uvicorn` stub with a real Typer-based CLI entrypoint. This is roadmap Foundation F-01 (`context/foundation/roadmap.md`): a minimal, invokable command surface that every vertical slice (S-01 inspect, S-02 search, S-03 redact) will attach real logic to. Also closes the mypy strict-config gap (`health-check.md` Fix #3) while the typed surface is still small enough that turning strict mode on costs nothing.

## Current State Analysis

`src/cover_data/__init__.py` is an 8-line stub (`def main() -> None: print("Hello from cover-data!")`). `pyproject.toml` lists `fastapi>=0.141.1` and `uvicorn>=0.52.4` as runtime dependencies — both inherited from the unrelated `trade-with-me` scaffold and already flagged as surplus in `CLAUDE.md`, `tech-stack.md`, and `stack-assessment.md`. No CLI framework is installed. `pyproject.toml` has no `[tool.mypy]` section, so `mypy` (already wired into `lefthook.yml` and both GitHub Actions workflows) runs under permissive defaults. `tests/test_smoke.py` only asserts the package imports — nothing currently exercises the CLI.

## Desired End State

`cover-data` is a Typer app with:
- `--version` at the top level, printing the installed package version and exiting 0.
- Three registered subcommands — `inspect`, `search`, `redact` — visible in `--help`, each currently a stub that prints a "not yet implemented" message naming its roadmap slice and exits 1.
- `fastapi`/`uvicorn` removed from dependencies; `typer` added.
- `[tool.mypy]` with `strict = true, files = ["src"]` in `pyproject.toml`.

Verification: `uv run cover-data --version` exits 0 with a version string; `uv run cover-data --help` lists `inspect`/`search`/`redact`; `uv run cover-data inspect` (etc.) exits 1 with a placeholder message; the full `lefthook.yml` pre-push gate (format-check, lint, lockfile, test, typecheck) passes.

### Key Discoveries:

- `stack-assessment.md`'s "Recommended Instruction File Additions" already drafted the exact convention to follow: commands as `@app.command()`-decorated functions in `src/cover_data/cli.py`, with `__init__.py`'s `main()` reduced to calling `app()`.
- `.github/workflows/release.yml:59-62` synthesizes `entry.py` as `from cover_data import main` + `main()` for the PyInstaller build — `cover_data.main` must stay a zero-argument callable that runs the whole CLI, or the release build breaks without any local signal.
- `.python-version` pins 3.14, so `bool | None` union syntax (used in Typer's own `--version` pattern) is available without `from __future__ import annotations` gymnastics, though `tests/test_smoke.py` already uses that import for consistency.
- `pyproject.toml`'s `[project.scripts]` entry (`cover-data = "cover_data:main"`) needs no change — only what `main()` does internally changes.

## What We're NOT Doing

- No real `inspect`/`search`/`redact` logic (OCR, row reconstruction, matching, redaction) — that's S-01/S-02/S-03, each planned separately once its own blocking Unknowns resolve.
- No argument signatures for the three stub subcommands — deciding what `inspect <image>` actually takes is progressive disclosure for S-01's own plan, not this Foundation's.
- No `rich`-based output or `typer.confirm()` prompts (FR-006/FR-007 territory) — nothing to confirm or preview yet.
- No changes to `release.yml`'s PyInstaller step — the existing `entry.py` synthesis already stays compatible as long as `cover_data.main` remains a zero-arg callable.

## Implementation Approach

Swap the dependency and tighten typing first (Phase 1), so the new CLI code is written directly against strict mypy rather than retrofitted. Then build the Typer app and its tests together (Phase 2), since the stub commands' behavior is only meaningfully verified through the tests that invoke them. Finish by documenting the now-real convention in `CLAUDE.md` (Phase 3) — writing the docs after the code exists avoids describing an API that then shifts during implementation.

## Critical Implementation Details

**Version source**: read the version via `importlib.metadata.version("cover-data")` rather than hardcoding a string in `cli.py` — `pyproject.toml`'s `version = "0.1.0"` is already the single source of truth; duplicating it invites drift.

**Combining `--version` with subcommands**: Typer's own `--version` tutorial pattern attaches the option to a single `@app.command()` function, which doesn't apply here since this app has three subcommands. Use `@app.callback()` instead — it runs before any subcommand dispatch — with the `--version` option marked `is_eager=True` so it short-circuits before Typer tries to resolve which subcommand was requested.

**Stub commands must exit non-zero**: each of `inspect`/`search`/`redact` should print its placeholder message and `raise typer.Exit(code=1)`, not exit 0. A stub that "succeeds" is indistinguishable from a real (currently impossible) success in scripts or tests that check the exit code.

## Phase 1: Dependency & config swap

### Overview

Remove the surplus web-framework dependencies, add Typer, and turn on strict mypy while `src/` is still two small files.

### Changes Required:

#### 1. Runtime dependencies

**File**: `pyproject.toml`, `uv.lock`

**Intent**: Drop `fastapi`/`uvicorn` (unused, inherited from the wrong project); add `typer` as the CLI framework, per `tech-stack.md` and `stack-assessment.md`'s already-drafted convention.

**Contract**: Run `uv remove fastapi uvicorn` then `uv add typer` (both need `--system-certs` on this network per `CLAUDE.md`). `uv.lock` regenerates automatically; do not hand-edit it.

#### 2. Strict mypy configuration

**File**: `pyproject.toml`

**Intent**: Close `health-check.md` Fix #3 — mypy currently runs under permissive defaults despite being gated on every commit.

**Contract**: Add a `[tool.mypy]` table with `strict = true` and `files = ["src"]`, matching the block already drafted in `stack-assessment.md`'s "Recommended Instruction File Additions".

### Success Criteria:

#### Automated Verification:

- Lockfile matches pyproject: `uv lock --check`
- Typecheck passes under new strict config: `uv run --locked mypy src`
- Existing suite still green: `uv run --locked pytest`

#### Manual Verification:

- `uv tree` no longer lists `fastapi` or `uvicorn`

---

## Phase 2: CLI scaffold + tests

### Overview

Build the Typer app (`--version` + three stub subcommands), wire `__init__.py`'s `main()` to it, and add tests that exercise the CLI in-process.

### Changes Required:

#### 1. Typer app

**File**: `src/cover_data/cli.py` (new)

**Intent**: The real command-registration surface. An `@app.callback()` handles the eager `--version` option; `inspect`, `search`, and `redact` are registered as `@app.command()` stubs, each printing a one-line "not yet implemented — see roadmap slice S-0N" message and raising `typer.Exit(code=1)`.

**Contract**: Exposes a module-level `app = typer.Typer()`. `--version` reads the installed version via `importlib.metadata.version("cover-data")`, prints it, and raises `typer.Exit()` — marked `is_eager=True` per the Critical Implementation Details above so it doesn't fight subcommand resolution.

#### 2. Entrypoint delegation

**File**: `src/cover_data/__init__.py`

**Intent**: `main()` becomes a thin delegate to the Typer app — no command logic lives here, matching `stack-assessment.md`'s convention and preserving `release.yml`'s `from cover_data import main; main()` contract.

**Contract**: `main() -> None` imports `app` from `cover_data.cli` and calls it with no arguments.

#### 3. CLI tests

**File**: `tests/test_cli.py` (new)

**Intent**: Exercise the CLI in-process using Typer's documented testing pattern, covering the behavior Phase 2 adds: version output, help listing, and each stub's placeholder exit.

**Contract**: Uses `typer.testing.CliRunner`. At minimum: `runner.invoke(app, ["--version"])` asserts exit code 0 and a version string in output; `runner.invoke(app, ["--help"])` asserts `inspect`, `search`, and `redact` all appear; one invocation per stub subcommand asserts exit code 1 and a "not yet implemented" message.

### Success Criteria:

#### Automated Verification:

- Full suite passes, including new CLI tests: `uv run --locked pytest`
- Typecheck passes: `uv run --locked mypy src`
- Lint and format checks pass: `uv run --locked ruff check .` and `uv run --locked ruff format --check .`

#### Manual Verification:

- `uv run cover-data --version` prints a version string and exits 0
- `uv run cover-data --help` lists `inspect`, `search`, and `redact`
- `uv run cover-data inspect` (and `search`, `redact`) prints a "not yet implemented" message and exits non-zero
- `uv run python -c "from cover_data import main; main()"` behaves the same as running `cover-data` directly with no arguments — confirms `release.yml`'s synthesized `entry.py` contract still holds

---

## Phase 3: Instruction file updates

### Overview

Document the CLI convention and the typing discipline now that both are real, using the blocks `stack-assessment.md` already drafted.

### Changes Required:

#### 1. CLI framework and typing discipline sections

**File**: `CLAUDE.md`

**Intent**: Close `health-check.md` Fix #4 — the compensation text `stack-assessment.md` drafted for the framework and mypy gaps has never been pasted into the instruction file agents actually read.

**Contract**: Add the two fenced blocks from `stack-assessment.md`'s "Recommended Instruction File Additions" section (`## CLI framework`, `## Typing discipline`) as new `##` sections in `CLAUDE.md`. Adjust command names in the CLI framework block if `inspect`/`search`/`redact` differ from what it assumes (it doesn't name specific commands, so no adjustment is expected).

### Success Criteria:

#### Automated Verification:

- Both new headings are present: `grep -q "## CLI framework" CLAUDE.md && grep -q "## Typing discipline" CLAUDE.md`

#### Manual Verification:

- The pasted sections accurately describe the code as implemented in Phase 2 (file paths, command names, the `[tool.mypy]` block match reality)

---

## Testing Strategy

### Unit Tests:

- `--version` prints a version string and exits 0
- `--help` lists all three subcommands
- Each stub subcommand exits 1 with a "not yet implemented" message
- Existing import smoke test (`tests/test_smoke.py`) continues to pass unmodified

### Integration Tests:

- None needed — this Foundation has no external systems to integrate with yet

### Manual Testing Steps:

1. Run `uv run cover-data --version` and confirm output and exit code
2. Run `uv run cover-data --help` and confirm all three subcommands are listed
3. Run `uv run cover-data inspect`, `search`, and `redact` individually and confirm each exits non-zero with a placeholder message
4. Run `uv run python -c "from cover_data import main; main()"` with no CLI args and confirm it behaves like running `cover-data` bare (Typer's default no-subcommand help/usage behavior), confirming the `release.yml` entrypoint contract

## Performance Considerations

None — this is a scaffold with no data processing.

## Migration Notes

None — the current `main()` stub has no real users; replacing its body is not a breaking change for anyone.

## References

- Roadmap Foundation: `context/foundation/roadmap.md` (F-01)
- Stack decision: `context/foundation/tech-stack.md`
- Drafted convention: `context/foundation/stack-assessment.md` ("Recommended Instruction File Additions")
- Health-check findings: `context/foundation/health-check.md` (Fix #2, #3, #4)
- Release build contract: `.github/workflows/release.yml:59-62`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Dependency & config swap

#### Automated

- [x] 1.1 Lockfile matches pyproject: `uv lock --check`
- [x] 1.2 Typecheck passes under new strict config: `uv run --locked mypy src`
- [x] 1.3 Existing suite still green: `uv run --locked pytest`

#### Manual

- [ ] 1.4 `uv tree` no longer lists `fastapi` or `uvicorn`

### Phase 2: CLI scaffold + tests

#### Automated

- [ ] 2.1 Full suite passes, including new CLI tests: `uv run --locked pytest`
- [ ] 2.2 Typecheck passes: `uv run --locked mypy src`
- [ ] 2.3 Lint and format checks pass: `uv run --locked ruff check .` and `uv run --locked ruff format --check .`

#### Manual

- [ ] 2.4 `uv run cover-data --version` prints a version string and exits 0
- [ ] 2.5 `uv run cover-data --help` lists `inspect`, `search`, and `redact`
- [ ] 2.6 `uv run cover-data inspect` (and `search`, `redact`) prints a "not yet implemented" message and exits non-zero
- [ ] 2.7 `uv run python -c "from cover_data import main; main()"` behaves the same as running `cover-data` directly with no arguments

### Phase 3: Instruction file updates

#### Automated

- [ ] 3.1 Both new headings are present: `grep -q "## CLI framework" CLAUDE.md && grep -q "## Typing discipline" CLAUDE.md`

#### Manual

- [ ] 3.2 The pasted sections accurately describe the code as implemented in Phase 2
