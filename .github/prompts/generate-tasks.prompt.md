---
mode: agent
---

# Task List Generation

You are to create a detailed, step-by-step task list in Markdown format based on an existing Product Requirements Document (PRD). The task list should guide a developer through implementation.

## Output

- **Format:** Markdown (`.md`)
- **Location:** `/tasks/`
- **Filename:** `tasks-[prd-file-name].md` (e.g., `tasks-prd-user-profile-editing.md`)

## Process

1.  **Receive PRD Reference:** The user points Copilot to a specific PRD file
2.  **Analyze PRD:** Copilot reads and analyzes the functional requirements, user stories, and other sections of the specified PRD.
3.  **Step 1: Generate Parent Tasks:** Based on the PRD analysis, create the file and generate the main, high-level tasks required to implement the feature. Use your judgement on how many high-level tasks to use, and derive how to assign these tasks in distinct phases. Present these tasks to the user in the specified format (without sub-tasks yet). Inform the user: "I have generated the high-level tasks based on the PRD. Ready to generate the sub-tasks? Respond with 'Go' to proceed."
4.  **Step 2: Generate Sub-Tasks:** Once the user confirms, break down each parent task into smaller, actionable sub-tasks necessary to complete the parent task. Ensure sub-tasks logically follow from the parent task and cover the implementation details implied by the PRD.
5.  **Identify Relevant Files:** Based on the tasks and PRD, identify potential files that will need to be created or modified. List these under the `Relevant Files` section, including corresponding test files if applicable.
6.  **Generate Final Output:** Combine the parent tasks, sub-tasks, relevant files, and notes into the final Markdown structure.
7.  **Save Task List:** Save the generated document in the `/tasks/` directory with the filename `tasks-[prd-file-name].md`, where `[prd-file-name]` matches the base name of the input PRD file (e.g., if the input was `prd-user-profile-editing.md`, the output is `tasks-prd-user-profile-editing.md`).

## Target Audience

Assume the primary reader of the task list is a **junior developer** who will implement the feature. Therefore, tasks should be explicit, unambiguous, and avoid jargon where possible.

## Task List Format

The generated task list _must_ follow this structure:

# Feature Development Plan

This task list is derived from the PRD: `[PRD path]`.

## Phase 1: [Phase Description, e.g., "Setup"]

- [ ] Task 1: [Parent Task Title]
  - [ ] 1.1 [Sub-task description 1.1]
  - [ ] 1.2 [Sub-task description 1.2]
- [ ] Task 2: [Parent Task Title]
  - [ ] 2.1 [Sub-task description 2.1]
        ...

## Phase X: [Phase Description, e.g. "Error Handling & Edge Cases"]

- [ ] Task X: [Parent Task Title] (may not require sub-tasks if purely structural or configuration)
