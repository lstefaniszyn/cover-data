# Copilot Coding Instructions for developer-platform-112511

## Overview

This project uses **AI Skills** for comprehensive development guidance. All detailed instructions have been consolidated into 4 specialized skills.

This repository also includes a **Bootstrap Orchestrator** flow for scaffolding a new plugin pair from the sample frontend/backend pair while preserving the sample templates, with explicit approval gates.

**Repository:** Backstage-based developer portal for Volvo  
**Focus:** Custom plugin development (frontend & backend)  
**Architecture:** Clean Architecture, Backstage patterns, DevOps best practices

---

## 🎯 Available Skills

The following skills provide comprehensive guidance for all development tasks:

### 1. **backstage-frontend-plugin**

**Use When:** Creating/modifying frontend plugin code, UI components, styling, Storybook

**Covers:**

- React 18+ with Material UI v5 (ALL UI components)
- VCDK design tokens and TailwindCSS styling
- VCDK SystemIcon (icons only)
- Clean Architecture (Pages → Containers → Components)
- Storybook-first development with MSW
- Testing (unit, integration, E2E with Playwright)

**Reference:** `.github/skills/skills-backstage-frontend-plugin/`

---

### 2. **backstage-backend-plugin**

**Use When:** Creating/modifying backend plugin code, APIs, databases

**Covers:**

- Clean Architecture (Domain → Services → Repositories → Controllers)
- Backstage backend-plugin-api patterns
- Express routing with Knex/PostgreSQL
- Error handling and HTTP response envelopes
- Database migrations (zero-downtime)
- Testing (unit, integration, contract, E2E with supertest)

**Reference:** `.github/skills/skills-backstage-backend-plugin/`

---

### 3. **clean-architecture-typescript**

**Use When:** Applying design patterns, refactoring, code quality improvements

**Covers:**

- Clean Code principles (naming, functions, SOLID)
- GoF Design Patterns (23 patterns with examples)
- TypeScript 5.x / ES2022 best practices
- Pattern selection and trade-offs
- Testing patterns for each design pattern

**Reference:** `.github/skills/skills-clean-architecture-typescript/`

---

### 4. **devops-continuous-delivery**

**Use When:** Setting up CI/CD, deployments, infrastructure, observability, incidents

**Covers:**

- Continuous Delivery practices (trunk-based, DORA metrics)
- Configuration management (externalized, feature flags)
- Database migrations (expand-contract pattern)
- Testing pyramid (risk-driven testing)
- Deployment strategies (blue-green, canary, rolling)
- Observability (logs, metrics, traces, health checks)
- Incident response (blameless post-mortems, MTTR)
- Security (shift-left, dependency scanning, secrets)

**Reference:** `.github/skills/skills-devops-continuous-delivery/`

---

## Quick Start Guide

### Bootstrap From Sample Pair (Use First For Scaffolding)

1. Start with the Bootstrap Orchestrator: `.github/agents/bootstrap.orchestrator.agent.md`
2. Follow staged flow: config -> preview/audit -> Gate A -> repo apply -> Gate B -> local install -> validation
3. Treat install contracts as automation source of truth
4. Use optional Gate C only for repository-level secret sync

### Speckit vs Bootstrap Orchestrator

1. Use Bootstrap Orchestrator for repo bootstrap and sample-pair scaffold/install workflow
2. Use Speckit agents for feature specification, planning, and implementation tasks

### Frontend Development

1. Use **Skill 1** (backstage-frontend-plugin)
2. All UI components: `@mui/material`
3. Icons only: `@volvo/vcdk-react/SystemIcon`
4. Styling: TailwindCSS + VCDK tokens

### Backend Development

1. Use **Skill 2** (backstage-backend-plugin)
2. Follow Clean Architecture layers
3. Use Knex for database queries
4. Implement health checks and observability

### Code Quality

1. Use **Skill 3** (clean-architecture-typescript)
2. Apply Clean Code principles
3. Choose appropriate design patterns
4. Write comprehensive tests

### DevOps & Infrastructure

1. Use **Skill 4** (devops-continuous-delivery)
2. Automate everything
3. Zero-downtime deployments
4. Observable and rollback-safe

---

## UI Component Priority (Quick Reference)

| Priority | Library                  | Use For                            |
| -------- | ------------------------ | ---------------------------------- |
| **1st**  | MUI v5 (`@mui/material`) | **ALL UI components**              |
| **2nd**  | TailwindCSS              | Styling, layout, spacing           |
| **3rd**  | VCDK SystemIcon          | **Icons ONLY** (1000+ Volvo icons) |

---

## Critical Rules

✅ **Always Do:**

- Use Bootstrap Orchestrator for sample-pair scaffolding instead of manual broad find/replace
- Use skills for comprehensive guidance
- Follow Clean Architecture patterns
- Write tests (80% coverage target)
- Run `yarn tsc --noEmit && yarn test --no-watch` before commit
- Use conventional commits
- Keep observability in mind (logs, metrics)

🚫 **Never Do:**

- Commit failing tests or TypeScript errors
- Hardcode secrets or environment-specific values
- Create custom UI components (use MUI v5)
- Skip database migration testing
- Deploy without rollback plan
- Bypass Gate A or Gate B approval when running bootstrap mutation stages

---

## MCP Tools Available

Use these tools to fetch up-to-date documentation:

| Tool                  | Purpose                                           |
| --------------------- | ------------------------------------------------- |
| `mcp_context7_*`      | Query library docs (Backstage, React, Knex, etc.) |
| `mcp_mui-mcp_*`       | Material UI v5 component documentation            |
| `mcp_backstageloca_*` | Query PostgreSQL databases                        |

**See:** `.github/skills/skills-backstage-frontend-plugin/references/mcp-integration.md` for detailed usage

---

## Development Workflow

```bash
# Start development
yarn start                    # Frontend + backend with hot reload

# Validate changes
yarn tsc --noEmit            # TypeScript check
yarn test --no-watch         # Run tests
yarn lint                    # Lint changed files

# Build
yarn build:backend           # Build backend
yarn build:all               # Build all packages
```

**Full commands reference:** `.github/skills/skills-backstage-frontend-plugin/references/yarn-workflows.md`

---

## For More Details

- **Skills Directory:** `.github/skills/skills-`
- **Tech Docs:** `techDocs/`
- **Project Specs:** `specs/`

<!-- BEGIN @przeprogramowani/10x-cli -->

## 10xDevs AI Toolkit - Module 3, Lesson 4 (E2E Tests)

**For E2E tests, use the `/10x-e2e` skill.** It is the single source of truth
for the workflow — risk → seed test + rules → generate → review against the five
anti-patterns → re-prompt → verify. The skill's `references/` carry the full
rules, anti-patterns, seed pattern, and prompt-template.

A few hard rules that hold even before you invoke the skill:

- **Locators:** `getByRole` / `getByLabel` / `getByText` first; `getByTestId`
  only when accessibility attributes are ambiguous. Never CSS selectors, XPath,
  or DOM structure.
- **Never `page.waitForTimeout()`.** Wait for state: `toBeVisible()`,
  `waitForURL()`, `waitForResponse()`.
- **Test independence + cleanup.** Each test runs standalone — its own setup,
  action, assertion, and cleanup; unique ids (timestamp suffix) so parallel runs
  and re-runs don't collide.

Two boundaries to keep straight:

- **DOM (snapshot) is the default.** Vision (`--caps=vision`) is a supplement for
  visual-only risks (layout, z-index, animation); for pixel regression prefer
  deterministic tools (`toMatchSnapshot`, Argos, Lost Pixel). VLM model
  selection/cost is a debugging topic (Lesson 5), not testing.
- **Healer helps on selectors, harms on logic.** A changed selector → healer
  re-finds it (route through PR review). A changed business behavior → healer
  masks the bug; that failing-test-to-fix case is Lesson 5.

<!-- END @przeprogramowani/10x-cli -->
