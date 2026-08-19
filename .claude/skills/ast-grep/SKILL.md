---
name: ast-grep
description: Use the ast-grep CLI for structural code search and rewrite in this repo — it parses syntax trees, so it finds symbols, call sites, exports, hooks, and patterns more precisely than grep. Use when asked to search code, locate usages, find where a function/component/schema is defined or called, or preview a codemod/rewrite across TS/TSX files.
---

# ast-grep — structural code search

Search TypeScript/TSX by AST pattern instead of text. Paths below are
relative to the repo root. Full CLI option tables:
[references/cli.md](references/cli.md).

## Prerequisites

```bash
ast-grep --version   # ast-grep 0.44.1 (alias: sg)
```

If missing: `npm install -g @ast-grep/cli` (on this machine prefix with
`NODE_OPTIONS=--use-system-ca` — corporate SSL interception breaks npm
otherwise).

## ast-grep vs. grep: complementary tools

ast-grep does not replace grep — it complements it. Their weaknesses are mirror images:

- **grep** is blunt but honest: searches raw text everywhere, so it finds the occurrence whether it's in code, a comment, or a similar variable name. False positives, but exhaustive.
- **ast-grep** is precise but picky: parses the syntax tree, so it only matches exact AST patterns. Zero matches from a structural query are suspicious — they often mean the pattern is wrong, not that the code doesn't exist.

**The rule:** Use ast-grep for precision, but confirm every zero result with grep. When ast-grep returns nothing, run the text search to verify it's not a pattern typo — a zero from the structural matcher means "my pattern didn't match the code as written," not necessarily "this code doesn't exist." Two cheap, deterministic tools watching each other — that's the discipline.

## Search (the main path)

**Always pass `-l ts` or `-l tsx`.** Without it ast-grep re-parses the
pattern per file language, and Markdown files in `src/` produce garbage
matches (a pattern like `Astro.locals` degenerates to matching bare `.`
tokens in `.md` files).

```bash
# call sites — $$$ matches any argument list
ast-grep -p 'createClient($$$)' -l ts src/

# metavariable capture — $X matches any single node
ast-grep -p '$X.locals' -l ts src/

# React hooks in components
ast-grep -p 'useState($$$)' -l tsx src/components/

# API route handlers
ast-grep -p 'export const $METHOD: APIRoute = $$$' -l ts src/pages/api/

# zod schemas
ast-grep -p 'z.object($$$)' -l ts src/

# by node kind, no pattern
ast-grep --kind interface_declaration -l tsx src/components/watchlist/

# structured output for scripting
ast-grep -p 'z.object($$$)' -l ts src/ --json=compact
```

Quote patterns in **single quotes** (both Git Bash and PowerShell) so
`$X` / `$$$` metavariables aren't expanded by the shell.

## Rewrite (preview by default)

ast-grep is not just a search tool — the same pattern that finds AST shapes can rewrite them structurally. Metavariables captured on the left (like `$A`, `$B`, `$$$`) are reused on the right, so rewrites preserve structure. This is **not** text search-and-replace: `ast-grep` distinguishes `Save` from `SaveMultiple` when rewriting (sed never will).

Without `-U`, ast-grep only **prints a diff** — files are not touched:

```bash
ast-grep -p 'createClient($$$A)' -r 'createServerClient($$$A)' -l ts src/middleware.ts
```

Review changes interactively (one by one) with `--interactive`, or apply all at once with `-U`:

```bash
ast-grep -p 'createClient($$$A)' -r 'createServerClient($$$A)' -l ts --interactive src/middleware.ts
ast-grep -p 'createClient($$$A)' -r 'createServerClient($$$A)' -l ts -U src/middleware.ts
```

For repeatable rewrites (part of a process, not one-off commands), save as a YAML rule with a `fix` field in your `sgconfig.yml` or a standalone rule file, then run `ast-grep scan`:

```yaml
id: rename-createClient
language: TypeScript
severity: info
message: "Renamed createClient to createServerClient"
rule:
  pattern: createClient($$$A)
fix: createServerClient($$$A)
```

Then: `ast-grep scan --rule ./rule.yaml --interactive` or `ast-grep scan` (if rules are in `sgconfig.yml`).

## Outline (file structure)

```bash
ast-grep outline src/lib/supabase.ts   # exported symbols with signatures
```

## Gotchas (all hit in this repo)

- **`.astro` files are silently skipped.** ast-grep has no Astro
  parser; `-l ts --globs '*.astro'` also yields nothing (lang filter
  goes by extension). Three `.astro` files containing `Astro.locals`
  matched zero times. → Use the Grep tool for `.astro` files.
- **Exit code 1 means "no matches"**, not an error. Don't retry or
  treat it as a failure.
- **Truncating pipes complain but the output is valid.** PowerShell
  `| Select-Object -First N` makes ast-grep exit 255; Git Bash
  `--json | head -c N` prints `The pipe is being closed. (os error
  232)`. In both cases the matches already printed are correct —
  ignore the error.
- **Omitting `-l` on a directory** searches every supported language
  including Markdown — see the warning above.
- Output paths mix `/` and `\` on Windows (e.g.
  `src/pages\api\sentiment.ts`); harmless, but normalize before diffing
  path lists.
