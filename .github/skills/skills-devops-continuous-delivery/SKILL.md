---
name: skills-devops-continuous-delivery
description: Apply DevOps and Continuous Delivery principles for building, testing, releasing, and running software. Use when (1) Setting up CI/CD pipelines for Backstage or any application, (2) Designing deployment strategies (blue-green, canary, rolling), (3) Implementing observability (logs, metrics, traces), (4) Managing environments and configuration, (5) Planning incident response and blameless post-mortems, (6) Establishing deployment gates and automated testing strategies, (7) Configuring infrastructure as code (Terraform, Helm, Kubernetes). Covers Build automation, deployment pipelines, environment parity, database migrations, security shift-left, incident response, and DORA metrics.
---

# DevOps & Continuous Delivery

## Core Principles

- Every change is **versioned**, **buildable**, **testable**, and **deployable** on demand
- **Automate everything** that is repeated: build, test, deployment, verification, rollback
- Ensure **environment parity** (dev/test/staging/prod behave the same)
- Keep the system **releasable** at all times; prefer **small, frequent** changes
- Make the delivery process **visible**, **measurable**, and **controllable** end-to-end

## Deployment Pipeline (Stages & Gates)

### Single Path to Production

```
Commit → Build → Unit Tests → Integration → Security → UAT → Staging → Production
  ↓        ↓         ↓            ↓            ↓        ↓       ↓          ↓
Pass    Artifact  Coverage     API Tests   SAST/DAST  Manual  Canary   100%
         Created  ≥80%                                Sign-off Deploy  Traffic
```

**Key Principles:**

- Each stage provides a **binary decision** (promote or stop)
- Promotion uses the **same artifact** (never rebuild downstream)
- Include **automated acceptance criteria** for business value/risk
- Make pipeline status and history **observable** to everyone

[See references/cd-practices.md for detailed pipeline patterns]

## Build & Artifact Management

### Build Requirements

✅ **MUST:**

- Single **build script** creates deployable artifacts from clean checkout
- Build is **deterministic** and **idempotent** (same input → same output)
- Outputs are **uniquely versioned** and **immutable**
- Store in **central artifact repository** (never rebuild downstream)
- Capture **build provenance**: source revision, dependencies, environment, parameters

❌ **NEVER:**

- Rebuild artifacts between stages
- Skip version tagging
- Use mutable tags (e.g., `latest` without SHA)
- Store artifacts locally only

### Backstage Context

```bash
# Build backend image
yarn build-image --tag backstage-backend:${GIT_SHA}

# Publish to registry
docker push registry.company.com/backstage-backend:${GIT_SHA}

# Deploy with immutable tag
helm upgrade backstage ./helm --set image.tag=${GIT_SHA}
```

## Environments & Configuration

### Environment Parity

**MUST match across environments:**

- OS and platform versions
- Dependencies and package versions
- Infrastructure topology (number of replicas, services)
- Security policies and network rules

**MAY vary between environments:**

- Configuration values (URLs, credentials, feature flags)
- Resource limits (CPU, memory)
- Data volumes (use synthetic data in lower environments)

### Configuration Management

✅ **DO:**

- **Externalize configuration** from binaries
- Manage per-environment config under version control
- Use dedicated secrets management system (Vault, AWS Secrets Manager, Azure Key Vault)
- Apply least privilege and rotation policies
- Use feature toggles for incomplete work

❌ **NEVER:**

- Hardcode environment-specific values in code
- Commit secrets to Git
- Use same credentials across environments
- Store secrets in plain text

[See references/configuration-patterns.md for Backstage-specific examples]

## Database & Schema Changes

### Evolutionary Database Design

**Pattern:** Expand-and-contract for zero-downtime changes

```
1. Expand: Add new column (nullable)
2. Deploy: Code reads both old and new
3. Migrate: Copy data from old → new
4. Deploy: Code writes to new only
5. Contract: Remove old column
```

**Key Principles:**

- Use **versioned, reversible migrations** (Knex.js for Backstage)
- Keep schemas **backward compatible** until all dependents updated
- Migrate data as part of pipeline with validation
- Test rollback paths for critical migrations

[See references/database-migrations.md for detailed patterns]

## Testing Strategy (Risk-Driven)

### Testing Pyramid

Apply in pipeline stages:

| Stage           | Tests       | Purpose                          | Gate Criteria         |
| --------------- | ----------- | -------------------------------- | --------------------- |
| **Commit**      | Unit        | Domain logic, pure functions     | >90% coverage, <2min  |
| **Integration** | Integration | HTTP + DB, API contracts         | All pass, <10min      |
| **Security**    | SAST/DAST   | Static analysis, dependency scan | No high/critical CVEs |
| **UAT**         | E2E         | Critical user journeys           | All smoke tests pass  |

**Non-Functional Testing:**

- **Performance:** Benchmark hot endpoints (<200ms P95), load tests
- **Security:** Auth/authz flows, input validation, secret detection
- **Accessibility:** WCAG 2.2 AA compliance, keyboard navigation
- **Reliability:** Inject failures (circuit breakers, timeouts, retries)

[See references/testing-pyramid.md for comprehensive guidance]

## Release & Deployment Strategies

### Strategy Selection

| Strategy       | When to Use                      | Rollback               | Complexity |
| -------------- | -------------------------------- | ---------------------- | ---------- |
| **Blue-Green** | Full environment swap            | Instant (flip traffic) | Medium     |
| **Canary**     | Gradual rollout with monitoring  | Route subset back      | High       |
| **Rolling**    | Update instances one-by-one      | Redeploy old version   | Low        |
| **Shadow**     | Test in prod without user impact | No user impact         | High       |

**Backstage Context:**

- **Recommended:** Rolling deployments with health checks
- **Advanced:** Canary with Prometheus metrics (error rate, latency)

### Health Checks

```typescript
// Backstage backend health check
export const healthCheck = async (req: Request, res: Response) => {
  const dbHealthy = await checkDatabase();
  const cacheHealthy = await checkCache();

  if (dbHealthy && cacheHealthy) {
    res.status(200).json({ status: "ok" });
  } else {
    res.status(503).json({ status: "degraded", db: dbHealthy, cache: cacheHealthy });
  }
};
```

[See references/deployment-strategies.md for detailed patterns]

## Observability & Monitoring

### Three Pillars

| Pillar      | Purpose               | Tools                 | Alert On                        |
| ----------- | --------------------- | --------------------- | ------------------------------- |
| **Logs**    | Debugging, auditing   | Structured JSON logs  | Error patterns, anomalies       |
| **Metrics** | Performance, capacity | Prometheus, Grafana   | Latency, error rate, saturation |
| **Traces**  | Request flow, latency | OpenTelemetry, Jaeger | Slow transactions, errors       |

**Key Metrics (DORA):**

- **Deployment Frequency** — How often you deploy
- **Lead Time for Changes** — Commit → production time
- **Change Failure Rate** — % of deployments causing incidents
- **Mean Time to Restore (MTTR)** — Time to recover from incidents

**Backstage Context:**

- Use `@backstage/backend-plugin-api` LoggerService for structured logging
- Integrate OpenTelemetry for distributed tracing
- Expose Prometheus metrics at `/metrics` endpoint

[See references/observability-patterns.md for Backstage-specific setup]

## Incident Response & Learning

### Incident Workflow

1. **Detect** + **Alert** — Automated monitoring triggers page
2. **Triage** — On-call determines severity, escalates if needed
3. **Mitigate** — Rollback, scale, or apply hotfix
4. **Resolve** — Verify service restored, clear alerts
5. **Post-Mortem** — Blameless review, action items with owners

### Blameless Post-Mortem Template

```markdown
## Incident: [Title]

**Date:** [YYYY-MM-DD]  
**Duration:** [Detection → Resolution]  
**Severity:** [SEV-1/2/3]

### What Happened

- [Timeline of events]

### Root Cause

- [Technical root cause]

### What Went Well

- [Good responses]

### What Went Poorly

- [Gaps, delays]

### Action Items

- [ ] [Action] (Owner: [Name], Due: [Date])
```

[See references/incident-response.md for detailed playbooks]

## Security & Compliance (Shift-Left)

### Pipeline Security Gates

| Gate                 | Stage      | Tools                   | Fail On                       |
| -------------------- | ---------- | ----------------------- | ----------------------------- |
| **Static Analysis**  | Commit     | SonarQube, ESLint       | Critical issues               |
| **Dependency Scan**  | Build      | Snyk, npm audit         | High/critical CVEs            |
| **Secret Detection** | Pre-commit | git-secrets, TruffleHog | Any secrets found             |
| **Container Scan**   | Build      | Trivy, Clair            | High/critical vulnerabilities |

**Best Practices:**

- Enforce **least privilege** in IAM policies and service accounts
- Use **defense in depth** (layered security controls)
- Implement **secure defaults** in infrastructure and applications
- Keep **audit trails** for all changes (code, config, runtime)
- Automate compliance evidence collection

[See references/security-patterns.md for detailed guidance]

## Pre-Merge Checklist

- [ ] Pipeline documented and versioned in repo
- [ ] All stages pass (build, test, security scan)
- [ ] Artifact tagged with immutable version (SHA)
- [ ] Configuration externalized (no hardcoded values)
- [ ] Database migrations reversible and tested
- [ ] Health checks implemented and tested
- [ ] Observability added (logs, metrics, traces)
- [ ] Rollback plan documented
- [ ] Feature flags in place for incomplete features
- [ ] Runbook updated if operational changes

## Reference Files

| Topic                      | Reference File                                                               |
| -------------------------- | ---------------------------------------------------------------------------- |
| **CD Practices**           | [references/cd-practices.md](references/cd-practices.md)                     |
| **Configuration Patterns** | [references/configuration-patterns.md](references/configuration-patterns.md) |
| **Database Migrations**    | [references/database-migrations.md](references/database-migrations.md)       |
| **Testing Pyramid**        | [references/testing-pyramid.md](references/testing-pyramid.md)               |
| **Deployment Strategies**  | [references/deployment-strategies.md](references/deployment-strategies.md)   |
| **Observability Patterns** | [references/observability-patterns.md](references/observability-patterns.md) |
| **Incident Response**      | [references/incident-response.md](references/incident-response.md)           |
| **Security Patterns**      | [references/security-patterns.md](references/security-patterns.md)           |

## Development Commands

```bash
# Build and test locally
yarn build:all && yarn test --no-watch

# Build Docker image
yarn build-image --tag backstage:${GIT_SHA}

# Run security scan
npm audit --audit-level=moderate

# Check migrations
knex migrate:latest --env test
```
