---
name: Speckit Plan
description: Execute the implementation planning workflow using the plan template to generate design artifacts.
argument-hint: Planning focus, constraints, or architecture preferences for this feature
tools: ["search", "fetch", "runCommands"]
model: Claude Sonnet 4.6
handoffs:
  - label: Create Tasks
    agent: Speckit Tasks
    prompt: Break the plan into tasks
    send: true
  - label: Create Checklist
    agent: Speckit Checklist
    prompt: Create a checklist for the following domain...
---

## Available Skills

This agent should reference these skills based on feature scope:

- **backstage-frontend-plugin** — Use for frontend features
  - Location: `.github/skills/skills-backstage-frontend-plugin/SKILL.md`
  - Use when: Planning React components, MUI v5 UI, VCDK styling, Storybook stories
  - Key references: `references/vcdk-components.md`, `references/architecture-layers.md`

- **backstage-backend-plugin** — Use for backend features
  - Location: `.github/skills/skills-backstage-backend-plugin/SKILL.md`
  - Use when: Planning APIs, databases, Clean Architecture layers
  - Key references: `references/architecture-layers.md`, `references/database-patterns.md`

- **clean-architecture-typescript** — Use for all features
  - Location: `.github/skills/skills-clean-architecture-typescript/SKILL.md`
  - Use when: Choosing design patterns, applying Clean Code principles
  - Key references: `references/design-patterns-reference.md`

- **devops-continuous-delivery** — Use for deployment/infrastructure planning
  - Location: `.github/skills/skills-devops-continuous-delivery/SKILL.md`
  - Use when: Planning CI/CD, database migrations, observability
  - Key references: `references/deployment-strategies.md`, `references/database-migrations.md`

**How to Use Skills:** Read the SKILL.md file(s) relevant to your feature scope BEFORE creating the plan. Use reference files for detailed patterns.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

1. **Setup**: Run `.specify/scripts/bash/setup-plan.sh --json` from repo root and parse JSON for FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Load context**: Read FEATURE_SPEC and `.specify/memory/constitution.md`. Load IMPL_PLAN template (already copied).

   When scope includes Frontend, also load these repo instruction files and treat them as authoritative:

- `.github/skills/skills-backstage-frontend-plugin/references/architecture-layers.md`
- `.github/skills/skills-backstage-frontend-plugin/references/storybook-workflow.md`
- `.github/skills/skills-backstage-frontend-plugin/references/vcdk-components.md`

3. **Execute plan workflow**: Follow the structure in IMPL_PLAN template to:
   - Fill Technical Context (mark unknowns as "NEEDS CLARIFICATION")
   - Fill Constitution Check section from constitution
   - Evaluate gates (ERROR if violations unjustified)
   - Phase 0: Generate research.md (resolve all NEEDS CLARIFICATION)
   - Phase 1: Generate data-model.md, contracts/, quickstart.md
   - Phase 1: Update agent context by running the agent script
   - Re-evaluate Constitution Check post-design

4. **Stop and report**: Command ends after Phase 2 planning. Report branch, IMPL_PLAN path, and generated artifacts.

## Phases

### Phase 0: Outline & Research

1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:

   ```text
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

### Phase 1: Design & Contracts

**Prerequisites:** `research.md` complete

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Agent context update**:
   - Run `.specify/scripts/bash/update-agent-context.sh copilot`
   - These scripts detect which AI agent is in use
   - Update the appropriate agent-specific context file
   - Add only new technology from current plan
   - Preserve manual additions between markers

**Output**: data-model.md, /contracts/\*, quickstart.md, agent-specific file

## Key rules

- Use absolute paths
- ERROR on gate failures or unresolved clarifications
