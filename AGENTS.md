# Repository Guidelines

Cover the Data is a single-user Python CLI that redacts every person except one from a scanned debtor list and writes the result as a new PDF. Stack per @context/foundation/tech-stack.md: Python managed with uv, explicit typing (type hints + Pydantic), pytest.

## Hard rules

- Redaction permanently overwrites pixels. A rectangle drawn over still-recoverable content fails the product's core guarantee.
- Never modify the source file. Output is always a separate artifact.
- Never auto-pick when a name search matches more than one row — require explicit confirmation first.
- Retain per-fragment OCR confidence and flag low-confidence reads; never silently trust them.
- No hosted OCR (Textract, Document AI, Azure). Debtor PII stays on the device.
- Ignore @.github/copilot-instructions.md entirely — it describes an unrelated Backstage portal.
- Always work inside the local `.venv`: prefix commands with `uv run`, which resolves it automatically. Never invoke system Python, `pip`, or bare `pytest`/`ruff`/`mypy` — `C:\Python314` is on PATH and is not this project's interpreter.

## Repository state

Scaffolded via uv into a src-layout package: `src/cover_data/`, `pyproject.toml` (requires-python >=3.14), `uv.lock`, and a `.venv`. Its `cover-data` console script still points at a `main` that does not exist yet. Root-level JS config (`tsconfig.json`, `eslint.config.js`, `vitest.config.ts`, `playwright.config.ts`, `.github/workflows/`) is leftover from an unrelated Astro project — replace it, don't extend it. See @CLAUDE.md for the full inventory and the two leftovers that actively break Python work.

## Spec

@context/foundation/prd.md is the contract; @context/README.md is the wider brief, deliberately broader than MVP scope, so the PRD wins on conflict. Work runs through the `/10x-*` skills: per-change state under `context/changes/<change-id>/`, durable spec under `context/foundation/`.

## Commands

`uv sync` to install; `uv run pytest`; `uv run pytest tests/test_smoke.py::test_name` for a single test; `uv run ruff check .`; `uv run mypy src`. This network runs a TLS-inspecting proxy, so any uv command that fetches needs `--system-certs` (or `UV_NATIVE_TLS=1`); `pip-audit` cannot be fixed that way and currently fails.

## Style and testing

Model OCR fragments, reconstructed rows, and match candidates as Pydantic types, not bare dicts — row geometry is the part that breaks silently. ruff formats and lints, mypy gates types. Mark fixture-heavy OCR and full-page redaction tests `@pytest.mark.slow`: @lefthook.yml runs `-m "not slow"` on pre-commit and the full suite on pre-push.

## Commits

One commit so far (`init project`), so no message convention is established — define one on the next. @lefthook.yml is installed and gates commits: ruff format/fix, fast tests, and mypy on pre-commit; lint, full suite, and `uv lock --check` on pre-push.
