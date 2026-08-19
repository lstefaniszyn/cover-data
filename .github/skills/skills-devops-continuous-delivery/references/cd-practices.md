# Continuous Delivery Practices

> Build repeatable, low-risk releases with automation and fast feedback loops.

## Core Principles

- Every change is **versioned**, **buildable**, **testable**, and **deployable** on demand
- **Automate everything** that is repeated: build, test, provisioning, deployment, verification, rollback
- Ensure **environment parity** so that what passes in earlier stages behaves the same in later stages
- Keep the system **releasable** at all times; prefer **small, frequent** changes
- Make the delivery process **visible**, **measurable**, and **controllable** end-to-end

---

## Trunk-Based Development & Branching

**Pattern:** Commit to a **single mainline** with short-lived branches; integrate at least daily.

**Rules:**

- Keep branches short-lived (<1 day)
- Integrate to main at least daily
- Use **feature toggles** to deliver incomplete work safely
- Use **branch by abstraction** for large refactorings
- Keep merges small; resolve conflicts early
- Avoid long-running release branches

**Anti-Patterns:**

- Long-lived feature branches (>1 week)
- Waiting for features to be "done" before merging
- Manual merge coordination
- Fear of breaking main branch

---

## Build & Artifact Management

**Pattern:** A single **build script** creates deployable artifacts from a clean checkout.

**Rules:**

- The build is **deterministic** and **idempotent**
- Outputs are uniquely versioned and immutable
- Store build outputs in a **central artifact repository**
- Artifacts flow forward, never rebuilt downstream
- Capture **build provenance**: source revision, dependencies, environment, parameters

**Example Build Provenance:**

```json
{
  "artifact": "my-plugin-backend:1.2.3",
  "gitSha": "abc123def",
  "buildTimestamp": "2024-01-15T10:30:00Z",
  "dependencies": {
    "@backstage/backend-plugin-api": "0.6.0",
    "express": "4.18.2"
  },
  "buildEnvironment": {
    "nodeVersion": "20.10.0",
    "yarnVersion": "4.0.0"
  }
}
```

---

## Continuous Integration

**Pattern:** Every commit triggers an **automatic build and test** run that finishes quickly and reports clearly.

**Rules:**

- The build must be **fast** (target <10 minutes for feedback)
- Optimize feedback loops and keep the main pipeline unblocked
- Red builds are treated as **production incidents** for the pipeline
- Fix forward immediately
- Prevent flaky validations; **quarantine**, deflake, or remove unstable checks

**Example CI Workflow:**

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Install dependencies
        run: yarn install --frozen-lockfile
      - name: Type check
        run: yarn tsc --noEmit
      - name: Lint
        run: yarn lint
      - name: Test
        run: yarn test --no-watch --coverage
      - name: Build
        run: yarn build:all
```

---

## Deployment Pipeline (Stages & Gates)

**Pattern:** Establish a **single path to production** with clearly named stages.

**Example Stages:**

1. **Commit** → Fast feedback (build, unit tests, lint)
2. **Acceptance** → Integration tests, contract tests
3. **Performance/Security** → Load tests, security scans
4. **UAT** → User acceptance testing
5. **Production** → Final deployment

**Rules:**

- Each stage provides a **binary decision** to promote or stop
- Promotion uses the **same artifact** (never rebuild)
- Include **automated acceptance criteria** representative of business value and risks
- Make pipeline status and history **observable** to everyone

**Example Gate Criteria:**

```yaml
# Promotion from Acceptance → Production
gates:
  - name: All tests pass
    status: required
  - name: Performance P95 < 200ms
    status: required
  - name: Security scan0 critical issues
    status: required
  - name: Manual approval from product owner
    status: optional
```

---

## DORA Metrics

Track these four key metrics:

| Metric                          | Definition                         | Target        |
| ------------------------------- | ---------------------------------- | ------------- |
| **Deployment Frequency**        | How often you deploy to production | Daily or more |
| **Lead Time for Changes**       | Time from commit to production     | < 1 day       |
| **Change Failure Rate**         | % of deployments causing failures  | < 15%         |
| **Mean Time to Restore (MTTR)** | Time to recover from failures      | < 1 hour      |

---

## Culture & Ways of Working

**Optimize for:**

- **Flow** — Small batch sizes, WIP limits
- **Feedback** — Fast loops
- **Learning** — Post-mortems, experiments

**Practices:**

- Encourage **pairing**, **mob reviews**, and **shared ownership**
- Use **hypothesis-driven** changes; measure outcomes
- Remove unused features to reduce complexity

---

## Pre-Merge Checklist

- [ ] Build script is deterministic and idempotent
- [ ] Artifacts are uniquely versioned
- [ ] Build provenance captured
- [ ] CI pipeline completes in <10 minutes
- [ ] Tests cover business-critical paths
- [ ] Pipeline stages are automated
- [ ] Feature flags in place for incomplete work
- [ ] DORA metrics tracked

---

**Golden Rule:** If it isn't automated, versioned, observable, and reversible, it is **not** done.
