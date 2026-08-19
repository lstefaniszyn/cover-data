# CLI Entrypoint Scaffold — Plan Brief

> Full plan: `context/changes/cli-entrypoint-scaffold/plan.md`

## What & Why

Replace the inherited `fastapi`/`uvicorn` stub in `src/cover_data/__init__.py` with a real Typer-based CLI entrypoint. This is roadmap Foundation F-01 — nothing else on the roadmap has anywhere to attach a user-invokable command until this lands.

## Starting Point

`main()` is an 8-line stub that just prints a greeting. `fastapi`/`uvicorn` are still installed as runtime dependencies despite being dead weight from an unrelated project. No CLI framework is chosen, `mypy` runs under permissive defaults, and nothing exercises the CLI in tests.

## Desired End State

Running `cover-data --version` prints the package version; `cover-data --help` lists three subcommands (`inspect`, `search`, `redact`) matching the roadmap's three vertical slices; each currently exits with a "not yet implemented" message until its own slice is built. `fastapi`/`uvicorn` are gone, `typer` is in, and mypy runs in strict mode.

## Key Decisions Made

| Decision                              | Choice                                                     | Why (1 sentence)                                                                 |
| -------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| Command structure                      | Subcommands (`inspect`/`search`/`redact`), registered now     | Matches the roadmap's three slices — `--help` becomes an honest, discoverable map of what's coming. |
| Stub behavior                          | Print a message, exit 1 — not silently succeed               | A stub that exits 0 is indistinguishable from a real success that can't exist yet. |
| Version flag                           | `importlib.metadata.version("cover-data")`, not hardcoded    | `pyproject.toml`'s `version` field stays the single source of truth.               |
| Mypy strict config                     | Bundled into this change                                     | Cheapest possible surface to turn strict mode on against, before any OCR/geometry code exists. |
| Test approach                          | `typer.testing.CliRunner` in pytest                          | Standard Typer-recommended pattern; fast, in-process, no subprocess overhead.       |

## Scope

**In scope:** removing `fastapi`/`uvicorn`, adding `typer`, a Typer app with `--version` + 3 stub subcommands, strict mypy config, CLI tests, documenting the convention in `CLAUDE.md`.

**Out of scope:** any real `inspect`/`search`/`redact` logic (OCR, row reconstruction, matching, redaction — each is its own future roadmap slice), argument signatures for the stub commands, `rich`/`typer.confirm()` UX (FR-006/FR-007, not needed until real logic exists).

## Architecture / Approach

One new file, `src/cover_data/cli.py`, holds a module-level `app = typer.Typer()`. An `@app.callback()` handles the eager `--version` flag (must run before subcommand dispatch); three `@app.command()` functions register the stub subcommands. `__init__.py`'s `main()` shrinks to `app()` — a thin delegate, preserving `release.yml`'s PyInstaller entrypoint contract (`from cover_data import main; main()`).

## Phases at a Glance

| Phase                          | What it delivers                                              | Key risk                                                                 |
| ------------------------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 1. Dependency & config swap     | `fastapi`/`uvicorn` out, `typer` in, strict mypy on                | Low — mechanical, direction already set by `tech-stack.md`.               |
| 2. CLI scaffold + tests         | Working `--version`, 3 stub subcommands, CliRunner test coverage  | Combining an eager `--version` with subcommands needs `@app.callback()`, not the single-command pattern Typer's own tutorial shows. |
| 3. Instruction file updates     | `CLAUDE.md` documents the CLI + typing conventions                | Low — copy from already-drafted text in `stack-assessment.md`.            |

**Prerequisites:** none — this is the first roadmap item.
**Estimated effort:** small, single session.

## Open Risks & Assumptions

- Assumes `release.yml`'s synthesized `entry.py` (`from cover_data import main; main()`) continues to work once `main()` delegates to a Typer app with subcommands — verified via manual step 2.7, not by actually running the Windows release build.
- Assumes strict mypy passes cleanly on the new small surface; if it doesn't, fixing type errors is within Phase 1/2 scope, not a blocker requiring a new decision.

## Success Criteria (Summary)

- `cover-data --version` and `--help` work as described; each stub subcommand fails loudly (exit 1) rather than silently succeeding.
- Full `lefthook.yml` gate (format, lint, lockfile, test, typecheck) passes.
- `fastapi`/`uvicorn` no longer appear anywhere in the dependency tree.
