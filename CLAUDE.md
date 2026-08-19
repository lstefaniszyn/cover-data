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

Pre-bootstrap and **pre-first-commit**. `git log` is empty, `git ls-files` returns nothing, every file in the tree is untracked. There is no source code, no `pyproject.toml`, no `src/`.

The next step in the workflow is `/10x-bootstrapper`, which reads `context/foundation/tech-stack.md`.

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

Already converted: `lefthook.yml` now runs ruff / mypy / pytest through `uv run --locked`. Its jobs fail until the project is scaffolded, so don't run `lefthook install` before `/10x-bootstrapper` (or bypass with `LEFTHOOK=0`).

## Stack

Python, managed with **uv**, packaged via `pyproject.toml`. Chosen for the ecosystem that carries the hard parts: OCR returning per-fragment bounding boxes *and* confidence, image/table geometry, and PDF assembly.

One wrinkle worth knowing: the tech-stack registry has no Python CLI card, so `tech-stack.md` records `starter_id: fastapi` as the closest Python vehicle — it was picked for its `uv` toolchain and typed-schema discipline, **not** because this is a web service. Bootstrapper's scaffold command ends in `uv add fastapi uvicorn`; drop both and add a CLI framework (Typer or Click) instead. If you find yourself standing up an HTTP server, something has gone wrong.

Match confirmation and row preview happen in the terminal plus an OS image viewer (the tool writes a cropped PNG and opens it) — deliberately chosen over a local web UI to keep this a true CLI.

Deployment target is `self-host` (a caseworker's machine). CI is GitHub Actions with manual promotion — there is nothing to auto-deploy to.

## Domain invariants

These come from the PRD and are the reason the project exists. Violating one silently is worse than failing loudly.

- **True redaction, never a visual cover-up.** Redacted pixels are permanently overwritten. A black rectangle drawn over recoverable content fails the guardrail.
- **The source file is never modified.** Output is always a separate artifact. This is a distinct testable requirement (FR-009), not an implied consequence of "we only read the file".
- **No silent auto-pick on an ambiguous match.** More than one matching row requires explicit user confirmation before any output is generated (FR-006).
- **OCR confidence is retained and low-confidence fragments are flagged**, never silently trusted (FR-002). Wrong-but-confident data is worse than no data.
- **Row geometry is first-class data.** The hard problem is not OCR — it is holding the OCR-fragment → cell → row → person relationship together when the scan is skewed or wavy. Get it wrong and the tool exposes the person who should have been hidden, or hides the one who should have stayed visible.
- **PII must not leave the device.** Hosted OCR APIs (Textract, Document AI, Azure) are excluded by an explicit avoid recorded in the stack decision. Local OCR only.
- **Temporary artifacts are cleaned up** once the operation that created them completes.

MVP boundaries that are deliberate, not oversights: image file input only (no PDF ingestion — that is a named fast-follow), exact-match search only, one document layout, no auth, no multi-user, printed text only.

**Blocking open question:** whether a real representative distorted scan exists to build and validate row reconstruction against. A clean synthetic sample cannot validate FR-003 or the exact-match assumption in FR-005 — those are precisely the requirements that fail on wavy geometry.

## The context/ workflow

This project is driven by the 10xDevs "10x-agents" context-driven methodology. State lives on disk under `context/`, not in chat history.

- `context/foundation/` — durable project spec. Currently holds `prd.md`, `shape-notes.md`, `tech-stack.md`. **Edit foundation docs in place**; when one is fully superseded rather than refined, move it to `context/foundation/archive/YYYY-MM-DD-<doc>.md` (see `context/foundation/README.md`).
- `context/changes/<change-id>/` — one folder per in-flight change, created by `/10x-new`, identified by `change.md`. Change-scoped research, frames, plans, and reviews go here — never in `foundation/`.
- `context/archive/` — completed changes, moved by `/10x-archive`.

Flow so far: `/10x-shape` → `/10x-prd` → `/10x-tech-stack-selector` ✅ → **`/10x-bootstrapper`** ← next → `/10x-roadmap`.

Then per roadmap slice: `/10x-new` → `/10x-research` → `/10x-frame` → `/10x-plan` → `/10x-plan-review` → `/10x-implement` / `/10x-tdd` / `/10x-e2e` → `/10x-impl-review` → `/10x-archive`.

Don't invent a different planning-artifact layout — extend `context/changes/<change-id>/`.

## Commands

**None of the usual commands work yet** — there is no project to run them against. Do not copy command lists out of the leftover JS config.

Once `/10x-bootstrapper` has scaffolded the project, commands follow standard uv conventions (`uv sync`, `uv run pytest`, `uv run pytest path/to/test_x.py::test_name` for a single test). Replace this section with the real commands from the generated `pyproject.toml` at that point rather than leaving these guesses in place.

## MCP

`.mcp.json` wires up `context7` (library docs) and `exa` (web search/fetch). Prefer `context7` over guessing at library APIs — the OCR/CV/PDF libraries this project depends on (PyMuPDF, OpenCV, Tesseract bindings, Pydantic, Typer, uv) move fast and their APIs are easy to confabulate.
