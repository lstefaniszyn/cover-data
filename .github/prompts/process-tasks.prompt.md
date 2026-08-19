---
mode: BackstageBackendDev
---

You are to work off of an existing task list, that follows specification file (PRD) mentioned in the task list file.
Process and update the existing tasks file to drive the implementation of a PRD.

## Scope

- Input: Reference of a tasks list Markdown file with numbered parent tasks and sub‑tasks.
- Output: The same file updated in place.
- Instructions:
  - .github/skills/skills-backstage-backend-plugin/references/architecture-layers.md while making tasks for Backend
  - .github/skills/skills-backstage-frontend-plugin/references/architecture-layers.md while making tasks for Frontend
- Follow the established folder structure and naming conventions.

## Modes:

- if user provies you `--all` that means you will process all subtasks and instead of asking for approval after each subtask, you will ask for approval after all subtasks are done.

## Working Rules

1. After completing a sub‑task, immediately update the tasks file:
   - Change [ ] to [x] for the finished sub‑task.
   - If all sub‑tasks under a parent are [x], also mark the parent as [x].
2. Pause after each update and ask for approval before proceeding.
3. Keep a "Relevant Files" section at the bottom of the file. List every file created or modified with a one‑line purpose.
4. Before starting, read the file and determine the next sub‑task.

## Save/Update

- Persist your changes to the same tasks file after each sub‑task.

## Task List Maintenance

1. **Update the task list as you work:**
   - Mark tasks and subtasks as completed (`[x]`) per the rules above.
   - Add new tasks as they emerge and call these out to the user.

2. **Maintain the “Relevant Files” section:**
   - List every file created or modified.
   - Give each file a one‑line description of its purpose.
   - Ensure this section is always at the bottom of the task list file.
