# Agents Manual (`agents.md`)

> **Purpose:** Define a clear, auditable workflow for agents to create, execute, test, document, and complete tasks using Markdown files inside the repository. This manual also provides an **audit template** to continuously improve project health.

---

## 1) Task Protocol

**Environment & specification requirements:**

* Maintain [`.codex/environment.md`](.codex/environment.md) with the exact commands required to prepare the Codex execution environment for this repository.
  * Update the file whenever dependencies, bootstrap scripts, or platform prerequisites change so future agents can reproduce your setup quickly.
  * If no setup is required beyond stock tooling, explicitly state that in the file and include any verification commands that confirm the environment is ready.
* Maintain [`.codex/SPEC.md`](.codex/SPEC.md) with the project’s high-level structure, goals, tech stack, architecture, and primary entry points.
  * Update the spec as the repository evolves so new contributors can quickly understand the context before working on tasks.

**Task files live in:**

* **Open tasks:** `.codex/tasks/`
* **Completed tasks:** `.codex/done/`

**Rules:**

1. If a task does **not** exist, **create it** as a Markdown file in `.codex/tasks/` using the [Task Template](#task-template) below.
2. When a task in `.codex/tasks/` is **executed and fully completed**, **move** the file to `.codex/done/`.
3. Any **pending or follow‑up items** discovered during task execution **must** be split into **new task files** in `.codex/tasks/` (one task per concern).
4. Keep tasks **atomic** and **scoped**. Prefer multiple small tasks over one overloaded task.
5. Use **standard Markdown links** for any files in this repository (e.g., [`README.md`](README.md), [`docs/`](docs/), [`.codex/docs/`](.codex/docs/)).
6. **One PR → one `.codex/done/` entry.** Each pull request must have a single `.codex/done/` Markdown log that summarizes all work covered by that PR. If the user requests additional updates on the same PR, **update the existing log file** instead of creating a new one so reviewers have a single source of truth.

**File naming convention:**

* New task: `.codex/tasks/<short-kebab-title>.md`
* Completed task: `.codex/done/<short-kebab-title>.md`
* If a name collision occurs, suffix with a timestamp or counter (e.g., `-2025-11-10` or `-v2`).

---

## 2) Post‑Task Requirements (Run After **Every** Task)

After completing any task (before moving it to `done`):

1. **Create tests and examples**

   * Add or update tests.
   * Whenever a task is completed, log every touched test case in the corresponding `.codex/done/` entry. This includes:
     * Newly created tests.
     * Modified or refactored tests.
     * Existing tests that explicitly cover code changed by the task (even if the test file itself was untouched).
   * Provide runnable examples (CLI, scripts, or code snippets).
   * If tests/examples **do not apply**, explicitly state **why** in the task file (in a **“Tests & Examples”** section) and notify the user.

2. **Update documentation**

   * Update relevant docs in `docs/`, `.codex/docs/`, and/or `README.md` **if updates are needed**.
   * Ensure docs reflect actual behavior and include usage examples.

3. **Lint & format** the codebase per the project standards.

4. **Commit messages** should reference the task filename and summarize changes.

---

## 3) Markdown Linking Rule

When writing `.md` files **with links to files accessible in this repo**, always use **standard Markdown links**. Examples:

* Link to README: [`README.md`](README.md)
* Link to repo docs: [`docs/`](docs/)
* Link to Codex docs: [`.codex/docs/`](.codex/docs/)
* Link to a sibling task: [`.codex/tasks/example-task.md`](.codex/tasks/example-task.md)

---

## 4) Task Template

Create each new task using the following template. Save it as `.codex/tasks/<short-kebab-title>.md`.

````markdown
# {{TASK_TITLE}}

- **ID**: {{TASK_ID}}
- **Created**: {{CREATED_AT_YYYY_MM_DD}}
- **Owner**: {{AGENT_OR_TEAM}}
- **Status**: Open

## Goal
Describe the outcome and success criteria.

## Plan
1. Step 1
2. Step 2
3. Step 3

## Deliverables
- Code changes and locations
- Updated docs (link exact files)
- Tests & examples

## Tests & Examples
- **Test strategy:** Unit/integration/e2e as applicable.
- **Commands to run tests:**
  ```bash
  {{TEST_COMMANDS}}
  ```

* **Examples (how to run/use the feature):**

  ```bash
  # CLI example(s)
  {{EXAMPLE_COMMANDS}}
  ```

* **If not applicable:** Explain **why** tests/examples do not apply.

## Linting & Quality

* **Commands to lint/format:**

  ```bash
  {{LINT_COMMANDS}}
  ```
* **Static analysis / type checks:**

  ```bash
  {{STATIC_ANALYSIS_COMMANDS}}
  ```

## Documentation Updates

List all doc files that must be updated and link them:

* [`README.md`](README.md)
* [`docs/<page>.md`](docs/)
* [`.codex/docs/<page>.md`](.codex/docs/)

## Notes / Risks

* Call out assumptions, migrations, or breaking changes.

## Completion Checklist

* [ ] Code implemented
* [ ] Tests written/updated and passing
* [ ] Examples added/updated
* [ ] Docs updated where needed
* [ ] Linting/formatting clean
* [ ] Review complete
* [ ] **Move this file to** `.codex/done/` **when all boxes are checked**

````

---

## 5) Audit Placeholder Template

> Use this template to perform a repository health audit for a specific folder or domain. The audit remains **in** `.codex/tasks/` **until it generates no new tasks**. Only then may it be moved to `.codex/done/`, and when moving it, **append the audit date** to the filename.

**Create at:** `.codex/tasks/{{folder_name}}-audit.md`

```markdown
# Audit: {{folder_name}}

- **Scope folder**: `{{folder_name}}`
- **Initiated**: {{YYYY_MM_DD}}
- **Owner**: {{AGENT_OR_TEAM}}
- **Status**: In Progress (keep this file in `.codex/tasks/` until no new tasks are generated)

## What to Check

### 1. Tasks Integrity
- [ ] **Pending tasks in `.codex/done/` that were never actually done** (misfiled items). If found, create corrective tasks in `.codex/tasks/`.

### 2. Tests & Examples
- [ ] Missing tests/examples where they should exist
- [ ] **Bad/insufficient test coverage** (define threshold & measure)
  - Record current coverage: `{{COVERAGE_PERCENT}}%`

### 3. Feature Parity vs Documentation
- [ ] **Missing features claimed in documentation** (feature parity gaps)
- [ ] Outdated instructions or broken examples in [`README.md`](README.md), [`docs/`](docs/), or [`.codex/docs/`](.codex/docs/)

### 4. Internal API Usage
- [ ] **Out‑of‑date usage of internal APIs** (deprecated calls, wrong signatures)
- [ ] Update call sites or migration notes as needed

### 5. Dependencies
- [ ] **Old dependencies** (pin versions, known CVEs, or upgrade guidance)
  - Record notable upgrades/fixes needed

## Findings
Describe each issue with links to files/lines when possible.

## Actions
For **every** finding above, create one or more **new tasks** in `.codex/tasks/` using the [Task Template](#task-template). Link them here for traceability.

- [ ] `{{NEW_TASK_LINK_1}}`
- [ ] `{{NEW_TASK_LINK_2}}`
- [ ] `{{NEW_TASK_LINK_3}}`

## Exit Criteria
- This audit file **must remain in** `.codex/tasks/` **until it produces no new tasks** on re‑run.
- When re‑running yields **no new tasks**, **move this file** to `.codex/done/` **and append the date** to the filename.
  - Example move: `.codex/done/{{folder_name}}-audit-{{YYYY_MM_DD}}.md`

## Verification Log
Document re‑runs of this audit and whether new tasks were created.
- {{YYYY_MM_DD}} – Re‑run; created 2 tasks: [`.codex/tasks/foo.md`](.codex/tasks/foo.md), [`.codex/tasks/bar.md`](.codex/tasks/bar.md)
- {{YYYY_MM_DD}} – Re‑run; **no** new tasks created → Eligible to move to done as `.codex/done/{{folder_name}}-audit-{{YYYY_MM_DD}}.md`
````

---

## 6) Examples

### Example: New feature task

* Create: `.codex/tasks/add-json-export.md`
* After completion, if tests/docs updated and all checkboxes are ticked, move to: `.codex/done/add-json-export.md`

### Example: Audit task

* Create: `.codex/tasks/api-audit.md`
* If re‑run produces no new tasks on {{YYYY_MM_DD}}, move to: `.codex/done/api-audit-{{YYYY_MM_DD}}.md`

---

## 7) Tips for Agents

* Prefer small PRs tied to a single task.
* Cross‑link tasks, audits, and docs using standard Markdown links.
* If you discover unrelated issues, **open separate tasks** instead of expanding scope.
* Keep templates up to date; evolve this manual via PRs.

3. **Lint & format** the codebase per the project standards.

4. **Commit messages** should reference the task filename and summarize changes.

---

## 3) Markdown Linking Rule

When writing `.md` files **with links to files accessible in this repo**, always use **standard Markdown links**. Examples:

* Link to README: [`README.md`](README.md)
* Link to repo docs: [`docs/`](docs/)
* Link to Codex docs: [`.codex/docs/`](.codex/docs/)
* Link to a sibling task: [`.codex/tasks/example-task.md`](.codex/tasks/example-task.md)

---

## 4) Task Template

Create each new task using the following template. Save it as `.codex/tasks/<short-kebab-title>.md`.

````markdown
# {{TASK_TITLE}}

- **ID**: {{TASK_ID}}
- **Created**: {{CREATED_AT_YYYY_MM_DD}}
- **Owner**: {{AGENT_OR_TEAM}}
- **Status**: Open

## Goal
Describe the outcome and success criteria.

## Plan
1. Step 1
2. Step 2
3. Step 3

## Deliverables
- Code changes and locations
- Updated docs (link exact files)
- Tests & examples

## Tests & Examples
- **Test strategy:** Unit/integration/e2e as applicable.
- **Commands to run tests:**
  ```bash
  {{TEST_COMMANDS}}
  ```

* **Examples (how to run/use the feature):**

  ```bash
  # CLI example(s)
  {{EXAMPLE_COMMANDS}}
  ```

* **If not applicable:** Explain **why** tests/examples do not apply.

## Linting & Quality

* **Commands to lint/format:**

  ```bash
  {{LINT_COMMANDS}}
  ```
* **Static analysis / type checks:**

  ```bash
  {{STATIC_ANALYSIS_COMMANDS}}
  ```

## Documentation Updates

List all doc files that must be updated and link them:

* [`README.md`](README.md)
* [`docs/<page>.md`](docs/)
* [`.codex/docs/<page>.md`](.codex/docs/)

## Notes / Risks

* Call out assumptions, migrations, or breaking changes.

## Completion Checklist

* [ ] Code implemented
* [ ] Tests written/updated and passing
* [ ] Examples added/updated
* [ ] Docs updated where needed
* [ ] Linting/formatting clean
* [ ] Review complete
* [ ] **Move this file to** `.codex/done/` **when all boxes are checked**

````

---

## 5) Audit Placeholder Template

> Use this template to perform a repository health audit for a specific folder or domain. The audit remains **in** `.codex/tasks/` **until it generates no new tasks**. Only then may it be moved to `.codex/done/`, and when moving it, **append the audit date** to the filename.

**Create at:** `.codex/tasks/{{folder_name}}-audit.md`

```markdown
# Audit: {{folder_name}}

- **Scope folder**: `{{folder_name}}`
- **Initiated**: {{YYYY_MM_DD}}
- **Owner**: {{AGENT_OR_TEAM}}
- **Status**: In Progress (keep this file in `.codex/tasks/` until no new tasks are generated)

## What to Check

### 1. Tasks Integrity
- [ ] **Pending tasks in `.codex/done/` that were never actually done** (misfiled items). If found, create corrective tasks in `.codex/tasks/`.

### 2. Tests & Examples
- [ ] Missing tests/examples where they should exist
- [ ] **Bad/insufficient test coverage** (define threshold & measure)
  - Record current coverage: `{{COVERAGE_PERCENT}}%`

### 3. Feature Parity vs Documentation
- [ ] **Missing features claimed in documentation** (feature parity gaps)
- [ ] Outdated instructions or broken examples in [`README.md`](README.md), [`docs/`](docs/), or [`.codex/docs/`](.codex/docs/)

### 4. Internal API Usage
- [ ] **Out‑of‑date usage of internal APIs** (deprecated calls, wrong signatures)
- [ ] Update call sites or migration notes as needed

### 5. Dependencies
- [ ] **Old dependencies** (pin versions, known CVEs, or upgrade guidance)
  - Record notable upgrades/fixes needed

## Findings
Describe each issue with links to files/lines when possible.

## Actions
For **every** finding above, create one or more **new tasks** in `.codex/tasks/` using the [Task Template](#task-template). Link them here for traceability.

- [ ] `{{NEW_TASK_LINK_1}}`
- [ ] `{{NEW_TASK_LINK_2}}`
- [ ] `{{NEW_TASK_LINK_3}}`

## Exit Criteria
- This audit file **must remain in** `.codex/tasks/` **until it produces no new tasks** on re‑run.
- When re‑running yields **no new tasks**, **move this file** to `.codex/done/` **and append the date** to the filename.
  - Example move: `.codex/done/{{folder_name}}-audit-{{YYYY_MM_DD}}.md`

## Verification Log
Document re‑runs of this audit and whether new tasks were created.
- {{YYYY_MM_DD}} – Re‑run; created 2 tasks: [`.codex/tasks/foo.md`](.codex/tasks/foo.md), [`.codex/tasks/bar.md`](.codex/tasks/bar.md)
- {{YYYY_MM_DD}} – Re‑run; **no** new tasks created → Eligible to move to done as `.codex/done/{{folder_name}}-audit-{{YYYY_MM_DD}}.md`
````

---

## 6) Examples

### Example: New feature task

* Create: `.codex/tasks/add-json-export.md`
* After completion, if tests/docs updated and all checkboxes are ticked, move to: `.codex/done/add-json-export.md`

### Example: Audit task

* Create: `.codex/tasks/api-audit.md`
* If re‑run produces no new tasks on {{YYYY_MM_DD}}, move to: `.codex/done/api-audit-{{YYYY_MM_DD}}.md`

---

## 7) Tips for Agents

* Prefer small PRs tied to a single task.
* Cross‑link tasks, audits, and docs using standard Markdown links.
* If you discover unrelated issues, **open separate tasks** instead of expanding scope.
* Keep templates up to date; evolve this manual via PRs.
