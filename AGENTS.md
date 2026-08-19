# Repository Guidelines

Cover the Data is a single-user Python CLI that redacts every person except one from a scanned debtor list and writes the result as a new PDF. Stack per @context/foundation/tech-stack.md: Python managed with uv, explicit typing (type hints + Pydantic), pytest.

## Hard rules

- Redaction permanently overwrites pixels. A rectangle drawn over still-recoverable content fails the product's core guarantee.
- Never modify the source file. Output is always a separate artifact.
- Never auto-pick when a name search matches more than one row — require explicit confirmation first.
- Retain per-fragment OCR confidence and flag low-confidence reads; never silently trust them.
- No hosted OCR (Textract, Document AI, Azure). Debtor PII stays on the device.
- Ignore @.github/copilot-instructions.md entirely — it describes an unrelated Backstage portal.

## Repository state

Pre-bootstrap and pre-first-commit: no `pyproject.toml`, no `src/`, and `git ls-files` returns nothing. Root-level JS config (`tsconfig.json`, `eslint.config.js`, `vitest.config.ts`, `playwright.config.ts`, `.github/workflows/`) is leftover from an unrelated Astro project — replace it, don't extend it. See @CLAUDE.md for the full inventory and the two leftovers that actively break Python work.

## Spec

@context/foundation/prd.md is the contract. @context/README.md is the wider brief and is deliberately broader than MVP scope; the PRD wins on conflict. Work is driven by the `/10x-*` skills, with per-change state under `context/changes/<change-id>/` and durable spec under `context/foundation/`.

## Commands

None work until `/10x-bootstrapper` scaffolds the project. After that: `uv sync`; `uv run pytest`; `uv run pytest tests/test_x.py::test_name` for a single test; `uv run ruff check .`; `uv run mypy src`.

## Style and testing

Model OCR fragments, reconstructed rows, and match candidates as Pydantic types, not bare dicts — row geometry is the part that breaks silently. ruff formats and lints, mypy gates types. Mark fixture-heavy OCR and full-page redaction tests `@pytest.mark.slow`: @lefthook.yml runs `-m "not slow"` on pre-commit and the full suite on pre-push.

## Commits

No history yet, so no convention is established — define one at the first commit. Hooks fail until bootstrap; don't run `lefthook install` before then, or bypass with `LEFTHOOK=0`.
