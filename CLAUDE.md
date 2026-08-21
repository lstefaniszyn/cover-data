# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

**Cover the Data** — a single-user Python CLI that takes a scanned debtor list, finds one named person, and writes a new PDF in which that person's row stays visible while every other row is permanently redacted at the pixel level.

Read these three before doing anything, in this order:

- `context/README.md` — the original project brief. Long and diagram-heavy; describes the full pipeline vision (PDF → page images → OCR → layout analysis → row reconstruction → redaction → output PDF). This is aspirational scope, not MVP scope.
- `context/foundation/prd.md` — **the contract.** Deliberately narrower than the brief. Every FR carries a `> Socrates:` note recording the counter-argument that was weighed and how it was resolved; don't reopen those without new information.
- `context/foundation/tech-stack.md` — the stack decision and its machine-readable hand-off frontmatter.

Where the brief and the PRD disagree, **the PRD wins**. The brief assumes a web app with uploads, multi-user access control, and a search index; the PRD cuts all of that.

## Repository state (read this first)

Scaffolded, with one commit (`init project`) behind it. `uv init` produced a src-layout package:

- `src/cover_data/__init__.py` — `main()` calling `app()`; `src/cover_data/cli.py` wires `inspect`/`search`/`redact` as stubs.
- `pyproject.toml` — `requires-python = ">=3.14"` today. Per `tech-stack.md`'s OCR engine decision this moves to `>=3.13` during `scan-row-reconstruction` (S-01) Phase 2, because `paddlepaddle`'s wheels stop at `cp313`; the downgrade is inert (no 3.14-only feature is used).
- `uv.lock` + `.venv/` — 15 packages, Python 3.14.7 today; recreate `.venv/` (`uv sync --locked`) after the 3.13 pin lands, or a stale 3.14 venv produces confusing failures.

`typer` is the only runtime dependency today (`fastapi`/`uvicorn`, once installed as surplus, have been removed — see Stack below). `scan-row-reconstruction` Phase 2 adds PaddleOCR — local, offline, model weights pre-placed in a git-ignored `models/` directory and never fetched at inference (`uv add --system-certs "paddleocr[doc-parser]" paddlepaddle`; ~97 resolved packages, no `torch`). `ruff`, `mypy`, and `pytest` are installed as dev dependencies, and `lefthook.yml` gates commits on all three.

**Always run through the local `.venv`.** Prefix commands with `uv run`, which resolves it automatically. Never call system Python, `pip`, or a bare `pytest`/`ruff`/`mypy` — `C:\Python314` is first on PATH and is not this project's interpreter. Activating the venv in a shell doesn't help across tool calls, since each Bash invocation gets a fresh environment.

**This network runs a TLS-inspecting proxy.** Any uv command that fetches needs `--system-certs` (or `UV_NATIVE_TLS=1`), or it dies with `invalid peer certificate: UnknownIssuer`. `pip-audit` can't be fixed that way — it uses `requests`/`certifi` rather than the system store, so the dependency tree is currently unaudited. Worth pinning the uv setting in `uv.toml`.

Bootstrap details and the full audit trail: `context/changes/bootstrap-verification/verification.md`.

## Inherited cruft — the biggest trap here

This repo was copied from a **different project** (`D:\Repo\trade-with-me`, an Astro + Supabase + Cloudflare stock-analysis app) and never cleaned. Most root-level config describes that app, not this one. `.claude/settings.local.json` still contains `trade-with-me` paths, which is the tell.

Treat all of the following as dead weight to be replaced, not as a stack to conform to:

| Leftover | Actually for |
|---|---|
| `tsconfig.json`, `eslint.config.js`, `vitest.config.ts`, `playwright.config.ts`, `.prettierrc.json` | the Astro/React app (`@/*` → `./src/*`, `astro:env` stubs, `MARKET_DATA_FIXTURE` fixture mode) |
| `.github/workflows/{ci,deploy}.yml` | npm + `astro sync` + local Supabase + Wrangler deploy + prod login smoke test |
| `.devcontainer/` | a Backstage/Storybook developer portal |
| `.gitignore` | a Backstage monorepo (Terraform, soundcheck, techdocs, yarn PnP) |
| `.github/copilot-instructions.md` | a Backstage developer portal for Volvo — **ignore it entirely**, wrong stack and wrong domain |
| `.yarnrc.yml` | neither this project nor the one it was copied from |
| root `README.md` | empty |

Two of these will actively break a Python workflow and should be fixed before writing code:

1. **`.claude/settings.json` PostToolUse hooks fire on every `Write|Edit`** — `npx eslint`, `npx tsc --noEmit`, and `node scripts/hooks/run-related-tests.mjs`. There is no `package.json` and no `scripts/hooks/`, so all three fail on every single file edit.
2. **`.claude/settings.json` permissions allow only `npm`/`npx`/`node`/`git`.** Every `uv`, `python`, `ruff`, and `pytest` invocation will prompt until that list is updated.

Real scaffold docs worth keeping: `context/README.md`, `context/foundation/README.md`, `context/changes/README.md`, `context/archive/README.md`, `.mcp.json`.

Already converted: `lefthook.yml` runs ruff / mypy / pytest through `uv run --locked`, and lefthook is installed (`uv tool install lefthook`) with hooks synced — commits are gated. `.claude/settings.json` now runs `.claude/hooks/post_edit_python.py` (ruff on edited `.py` files only) instead of the ESLint/tsc/Vitest trio.

## Stack

Python, managed with **uv**, packaged via `pyproject.toml`. Chosen for the ecosystem that carries the hard parts: OCR returning per-fragment bounding boxes *and* confidence, image/table geometry, and PDF assembly.

One wrinkle worth knowing: the tech-stack registry has no Python CLI card, so `tech-stack.md` records `starter_id: fastapi` as the closest Python vehicle — it was picked for its `uv` toolchain and typed-schema discipline, **not** because this is a web service. The scaffold originally installed `fastapi` and `uvicorn` as surplus; both have since been removed in favor of Typer (see "CLI framework" below). **If you find yourself standing up an HTTP server, something has gone wrong.**

Match confirmation and row preview happen in the terminal plus an OS image viewer (the tool writes a cropped PNG and opens it) — deliberately chosen over a local web UI to keep this a true CLI.

Deployment target is `self-host` (a caseworker's machine). CI is GitHub Actions with manual promotion — there is nothing to auto-deploy to.

## CLI framework

Commands are built with Typer, not bare `argparse` or a hand-rolled `sys.argv` parser.

- Each user-facing command is a function decorated with `@app.command()` in `src/cover_data/cli.py`; `src/cover_data/__init__.py`'s `main()` only calls `app()` — it holds no command logic itself.
- Command parameters use type hints (`Annotated[str, typer.Argument(...)]` / `typer.Option(...)`) — Typer derives validation and `--help` text from them, so an untyped parameter is a bug, not a style choice.
- Match-confirmation and row-preview prompts (see PRD FR-006, FR-007) go through Typer's `typer.confirm()` / `rich`-based output, not raw `input()`.
- `inspect`, `search`, and `redact` are the three registered subcommands, matching roadmap slices S-01/S-02/S-03 (`context/foundation/roadmap.md`). Each is currently a stub that exits 1 with a "not yet implemented" message until its slice lands — replace the stub body, don't restructure the command.

## Typing discipline

`mypy` runs on every commit (`lefthook.yml`) and in CI (`ci.yml`, `release.yml`) under `[tool.mypy] strict = true, files = ["src"]` (`pyproject.toml`).

OCR fragments, table rows, and person-match results are typed data structures (Pydantic models or `@dataclass`, not raw `dict`s) — this is a domain invariant, not a style preference: the hard problem in this project is keeping the OCR-fragment → cell → row → person relationship correct under skewed/wavy scans (see "Domain invariants" below), and an untyped dict makes a shape mismatch invisible until runtime.

## Domain invariants

These come from the PRD and are the reason the project exists. Violating one silently is worse than failing loudly.

- **True redaction, never a visual cover-up.** Redacted pixels are permanently overwritten. A black rectangle drawn over recoverable content fails the guardrail.
- **The source file is never modified.** Output is always a separate artifact. This is a distinct testable requirement (FR-009), not an implied consequence of "we only read the file".
- **No silent auto-pick on an ambiguous match.** More than one matching row requires explicit user confirmation before any output is generated (FR-006).
- **OCR confidence is retained and low-confidence fragments are flagged**, never silently trusted (FR-002). Wrong-but-confident data is worse than no data.
- **Row geometry is first-class data.** The hard problem is not OCR — it is holding the OCR-fragment → cell → row → person relationship together when the scan is skewed or wavy. Get it wrong and the tool exposes the person who should have been hidden, or hides the one who should have stayed visible.
- **PII must not leave the device.** Hosted OCR APIs (Textract, Document AI, Azure) are excluded by an explicit avoid recorded in the stack decision. Local OCR only.
- **Temporary artifacts are cleaned up** once the operation that created them completes.

MVP boundaries that are deliberate, not oversights: image file input only (no PDF ingestion — that is a named fast-follow), exact-match search only, a family of bordered debtor-table layouts with per-document column detection (not a single fixed schema — PRD Open Question #2, resolved 2026-08-21), no auth, no multi-user, printed text only.

**Searchable fields (FR-004).** A query is matched against `Imię`, `Nazwisko`, `Imię i nazwisko`, or `PESEL`, selected via an explicit `--field` option that defaults to full name when omitted — a documented default, not shape-based auto-detection. PESEL comparison is digits-only on both sides; a checksum failure is never a rejection, only evidence of possible OCR error. S-01 delivers the column-role vocabulary this depends on: `lp`, `imie`, `nazwisko`, `imie_i_nazwisko`, `pesel`, `adres`, `kwota`, `wierzyciel`, plus `unknown` for a header that doesn't resolve — matching the header text actually rendered across the three layouts: **A** renders `Lp.` / `Imię` / `Nazwisko` / `PESEL` / `Adres zamieszkania` / `Kwota zadłużenia (PLN)` / `Wierzyciel`; **B** renders `Lp.` / `Imię i nazwisko` / `PESEL` / `Adres` / `Kwota zadłużenia (PLN)` / `Wierzyciel`; **C** renders `Imię` / `Nazwisko` / `PESEL` / `Adres` / `Kwota zadłużenia (PLN)` / `Wierzyciel` — split name like A but no `Lp.`, and `Adres` (not `Adres zamieszkania`) like B.

**Blocking open question:** whether a real representative distorted scan exists to build and validate row reconstruction against. A clean synthetic sample cannot validate FR-003 or the exact-match assumption in FR-005 — those are precisely the requirements that fail on wavy geometry. **Fixture-set reality (2026-08-21):** `context/test_images/` now holds 26 fixtures indexed by `manifest.json` — `1.png`–`6.png` (image-model output, no ground truth, no PESEL column) and `7.png`–`26.png` (script-generated, exact-by-construction row content and, per `scan-row-reconstruction` Phase 3, exact warped geometry). The generated set is more controlled than the originals — exact ground truth, but still one generator's idea of a scan — so it narrows but does not close this question. See `context/foundation/test-plan.md` §2.

## The context/ workflow

This project is driven by the 10xDevs "10x-agents" context-driven methodology. State lives on disk under `context/`, not in chat history.

- `context/foundation/` — durable project spec. Currently holds `prd.md`, `shape-notes.md`, `tech-stack.md`. **Edit foundation docs in place**; when one is fully superseded rather than refined, move it to `context/foundation/archive/YYYY-MM-DD-<doc>.md` (see `context/foundation/README.md`).
- `context/changes/<change-id>/` — one folder per in-flight change, created by `/10x-new`, identified by `change.md`. Change-scoped research, frames, plans, and reviews go here — never in `foundation/`.
- `context/archive/` — completed changes, moved by `/10x-archive`.

Flow so far: `/10x-shape` → `/10x-prd` → `/10x-tech-stack-selector` ✅ → `/10x-bootstrapper` ✅ → **`/10x-roadmap`** ← next.

Then per roadmap slice: `/10x-new` → `/10x-research` → `/10x-frame` → `/10x-plan` → `/10x-plan-review` → `/10x-implement` / `/10x-tdd` / `/10x-e2e` → `/10x-impl-review` → `/10x-archive`.

Don't invent a different planning-artifact layout — extend `context/changes/<change-id>/`.

## Commands

Everything goes through `uv run` so it lands in `.venv`. Do not copy command lists out of the leftover JS config.

```bash
uv sync                                    # install from uv.lock
uv add <pkg> / uv remove <pkg>             # add --system-certs on this network
uv run pytest                              # once pytest is a dev dependency
uv run pytest tests/test_x.py::test_name   # single test
uv run ruff check . / uv run ruff format . # once ruff is a dev dependency
uv run mypy src                            # once mypy is a dev dependency
uv lock --check                            # verify uv.lock matches pyproject.toml
```

`ruff` 0.16.3, `mypy` 2.3.1, and `pytest` 9.1.1 are installed as dev dependencies. `[tool.ruff] extend-exclude` in `pyproject.toml` keeps linting off the vendored agent tooling in `.github/`, `.agents/`, `.codex/`, and `.claude/` — without it `ruff check .` fails on scripts this project doesn't own. `pytest -m 'not slow'` is the pre-commit gate; the `slow` marker (registered in `pyproject.toml`) is for fixture-heavy OCR or full-page redaction tests and only runs on pre-push/CI/release.

The fixture generator at `context/test_images/generate_edge_cases.py` is fixture tooling, not product code, and deliberately stays outside the project's dependency graph:

```bash
uv run --with pillow --with numpy --no-project python context/test_images/generate_edge_cases.py
```

OCR model weights live in a git-ignored `models/` directory, provisioned locally before any test that touches the real engine — provisioning steps land with the dependency stack in `scan-row-reconstruction` Phase 2.

## MCP

`.mcp.json` wires up `context7` (library docs) and `exa` (web search/fetch). Prefer `context7` over guessing at library APIs — the OCR/CV/PDF libraries this project depends on (PyMuPDF, OpenCV, Tesseract bindings, Pydantic, Typer, uv) move fast and their APIs are easy to confabulate.
