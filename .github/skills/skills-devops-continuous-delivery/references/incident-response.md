# Incident Response & Learning Culture

> Respond to incidents systematically, minimize MTTR, and learn from failures without blame.

## Core Principle

**Incidents are learning opportunities.** Focus on reducing MTTR (Mean Time To Restore), not preventing all failures.

---

## Incident Severity Levels

| Level             | Impact                          | Response Time     | Examples                             |
| ----------------- | ------------------------------- | ----------------- | ------------------------------------ |
| **P0 (Critical)** | Service down or major data loss | Immediate         | API down, database corrupted         |
| **P1 (High)**     | Service degraded for many users | <15 minutes       | High error rate, slow response times |
| **P2 (Medium)**   | Service degraded for some users | <1 hour           | Feature broken, minor data loss      |
| **P3 (Low)**      | Minor issue, no user impact     | Next business day | UI glitch, non-critical warning      |

---

## Incident Response Process

### 1. Detection (Automated)

**Pattern:** Alerts fire when **SLOs are breached** (not arbitrary thresholds).

**Example:**

```yaml
# Alert on error rate > 5% for 5 minutes
ErrorRateBreach:
  condition: error_rate > 5%
  duration: 5 minutes
  severity: P1
  action: Page on-call engineer
```

---

### 2. Triage (Quick Assessment)

**Pattern:** Quickly assess severity and assign roles.

**Roles:**

- **Incident Commander** — Coordinates response, makes decisions
- **Responders** — Investigate and fix the issue
- **Communications Lead** — Updates stakeholders

**Triage Questions:**

1. What is the user impact? (How many users affected?)
2. What services are affected?
3. What changed recently? (deployments, config, data)
4. Is this a known issue?

---

### 3. Mitigation (Restore Service)

**Pattern:** **Restore service first**, investigate root cause later.

**Fast Mitigation Options:**

1. **Rollback** deployment (< 5 minutes)
2. **Toggle off** feature flag (< 1 minute)
3. **Scale up** resources (< 5 minutes)
4. **Failover** to backup service (< 10 minutes)
5. **Disable** problematic feature (< 2 minutes)

**Example Rollback:**

```bash
# Kubernetes rollback to previous deployment
kubectl rollout undo deployment/backstage-backend

# Verify rollback successful
kubectl rollout status deployment/backstage-backend

# Check health endpoint
curl http://backstage-backend/health
```

---

### 4. Communication (Stakeholders)

**Pattern:** Regular updates every 15-30 minutes during active incident.

**Status Page Template:**

```markdown
**Incident: High Error Rate on Event Creation**
_Status: Investigating_
_Severity: P1_
_Start Time: 2024-01-15 14:30 UTC_

**14:30 UTC** - We are investigating reports of high error rates when creating events. Users may experience failures when submitting new events.

**14:45 UTC** - We have identified the issue as a database connection pool exhaustion. We are rolling back the latest deployment.

**15:00 UTC** - Rollback complete. Error rates have returned to normal. We are monitoring the situation.

**15:30 UTC** - Incident resolved. All services operating normally. Post-mortem to follow.
```

---

### 5. Resolution (Verify Fix)

**Pattern:** Confirm metrics return to normal before declaring incident resolved.

**Verification Checklist:**

- [ ] Error rate < 1% for 15 minutes
- [ ] Response time P95 < target for 15 minutes
- [ ] No alerts firing
- [ ] Critical user journeys tested
- [ ] Stakeholders notified of resolution

---

### 6. Post-Mortem (Learning)

**Pattern:** Blameless post-mortem within 48 hours after incident resolution.

**Post-Mortem Template:**

```markdown
# Post-Mortem: High Error Rate on Event Creation

**Date:** 2024-01-15
**Severity:** P1
**MTTR:** 30 minutes
**Responders:** Alice (IC), Bob (Responder), Carol (Comms)

## Summary

Database connection pool exhausted after deployment of new feature, causing 15% error rate on event creation for 30 minutes.

## Timeline

- **14:30** - Alert fired: error rate > 5%
- **14:32** - Incident declared (P1), Alice assigned as IC
- **14:35** - Investigation: Database logs show connection pool exhaustion
- **14:40** - Decision: Rollback to previous deployment
- **14:45** - Rollback initiated via kubectl
- **14:52** - Error rate returned to normal
- **15:00** - Incident resolved

## Root Cause

New feature introduced a database connection leak. Connections were not properly released after queries, leading to pool exhaustion after ~1000 requests.

## Impact

- 15% of event creation requests failed (500 Internal Server Error)
- ~150 users affected
- 30 minutes of degraded service

## What Went Well

- Alert fired within 2 minutes of error rate threshold breach
- Rollback process was straightforward and fast
- Clear communication to stakeholders every 15 minutes

## What Could Be Improved

- Connection leak not caught in code review or testing
- No integration test for connection pool exhaustion
- Monitoring dashboard lacked database connection pool metrics

## Action Items

- [ ] Add integration test for connection pool exhaustion (@Bob, due 2024-01-20)
- [ ] Add database connection pool metrics to dashboard (@Alice, due 2024-01-18)
- [ ] Update code review checklist to verify connection cleanup (@Carol, due 2024-01-17)
- [ ] Add automated connection leak detection to CI (@Bob, due 2024-01-25)
```

---

## MTTR Optimization

**Target:** MTTR < 1 hour (preferably < 15 minutes)

**Techniques:**

1. **Automated rollback** — Detect degradation, rollback automatically
2. **Feature flags** — Instant disable without deployment
3. **Runbooks** — Step-by-step incident response guides
4. **Observability** — Fast diagnosis with logs/metrics/traces
5. **On-call rotation** — 24/7 coverage with clear escalation

---

## Runbooks

**Pattern:** Step-by-step guides for common incidents.

**Example Runbook:**

```markdown
# Runbook: High Database CPU

## Symptoms

- Database CPU > 80% for > 5 minutes
- Slow query response times (P95 > 2 seconds)

## Diagnosis

1. Check CloudWatch Metrics for database CPU usage
2. Run `SHOW PROCESSLIST` to see active queries
3. Check slow query log for problematic queries

## Mitigation

1. Kill long-running queries: `KILL <query_id>`
2. Scale up database instance (if CPU sustained > 80%)
3. Add indexes to slow queries (if query patterns identified)

## Escalation

If CPU remains > 80% after 15 minutes:

- Page DBA on-call
- Consider read replica to offload read queries
```

---

## Blameless Culture

**Anti-Patterns:**

- "Who broke it?" (focus on systems, not individuals)
- "Why didn't you test this?" (hindsight bias)
- Punishing mistakes (creates fear, hides issues)

**Best Practices:**

- Focus on **what** happened, not **who** did it
- Assume **good intent** and **rational decisions** given available information
- Ask "How can we prevent this **system failure** in the future?"
- Celebrate **learning** and **improvement**

---

## On-Call Best Practices

**Rules:**

- On-call rotation shared across team (no single hero)
- Clear escalation path (who to call if stuck)
- Runbooks for common incidents
- Post-incident time off or compensation
- Limit on-call to 1 week per person per month

**Example On-Call Schedule:**

```
Week 1: Alice (Primary), Bob (Secondary)
Week 2: Carol (Primary), Dave (Secondary)
Week 3: Bob (Primary), Alice (Secondary)
Week 4: Dave (Primary), Carol (Secondary)
```

---

## Pre-Merge Checklist

- [ ] Incident severity levels defined
- [ ] Alerting configured (SLO breaches, not arbitrary thresholds)
- [ ] Runbooks created for common incidents
- [ ] On-call rotation established
- [ ] Rollback process tested and documented
- [ ] Post-mortem template ready
- [ ] Blameless culture emphasized in team norms
- [ ] MTTR target defined (< 1 hour)

---

**Golden Rule:** If an incident happens more than once, **automate the fix** or **prevent it with better design**.
