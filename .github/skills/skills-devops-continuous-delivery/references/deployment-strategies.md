# Deployment & Release Strategies

> Separate deployment from release; deploy often, release carefully with rollback plans.

## Core Principle

**Deployment** (putting code in production) is decoupled from **Release** (making features available to users). Deploy frequently with low risk using automated strategies.

---

## Blue-Green Deployment

**Pattern:** Maintain two identical environments (Blue and Green); switch traffic between them.

**How It Works:**

1. **Blue** environment serves production traffic
2. Deploy new version to **Green** environment
3. Run smoke tests on Green
4. Switch traffic from Blue → Green
5. Keep Blue as instant rollback target

**Pros:**

- Zero-downtime deployments
- Instant rollback (flip traffic back)
- Full testing in production-like environment

**Cons:**

- Requires double infrastructure capacity
- Database migrations must be backwards-compatible

**Example (Kubernetes):**

```yaml
# Service switches between blue and green deployments
apiVersion: v1
kind: Service
metadata:
  name: backstage-backend
spec:
  selector:
    app: backstage-backend
    version: green # Switch to 'blue' for rollback
  ports:
    - port: 80
      targetPort: 7007
```

---

## Canary Deployment

**Pattern:** Gradually roll out new version to a subset of users; monitor for issues.

**How It Works:**

1. Deploy new version to small % of instances (e.g., 5%)
2. Monitor metrics (errors, latency, business KPIs)
3. Gradually increase traffic (5% → 25% → 50% → 100%)
4. Rollback if metrics degrade

**Pros:**

- Limits blast radius of issues
- Real user feedback on new version
- Gradual confidence building

**Cons:**

- Requires traffic splitting infrastructure
- More complex monitoring setup

**Example Traffic Split (Istio):**

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: backstage-backend
spec:
  hosts:
    - backstage-backend
  http:
    - match:
        - headers:
            canary:
              exact: "true"
      route:
        - destination:
            host: backstage-backend
            subset: v2
          weight: 10 # 10% of traffic to new version
        - destination:
            host: backstage-backend
            subset: v1
          weight: 90 # 90% of traffic to current version
```

---

## Rolling Deployment

**Pattern:** Replace instances one-by-one until all run the new version.

**How It Works:**

1. Deploy new version to one instance
2. Remove old instance from load balancer
3. Verify new instance is healthy
4. Repeat for remaining instances

**Pros:**

- No extra infrastructure needed
- Simple and widely supported

**Cons:**

- Both versions run simultaneously (requires backwards compatibility)
- Rollback slower (must redeploy)

**Example (Kubernetes):**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backstage-backend
spec:
  replicas: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1 # Max 1 pod down at a time
      maxSurge: 1 # Max 1 extra pod during rollout
  template:
    spec:
      containers:
        - name: backend
          image: backstage-backend:1.2.3
          readinessProbe:
            httpGet:
              path: /health
              port: 7007
            initialDelaySeconds: 10
```

---

## Feature Flags (Dark Launches)

**Pattern:** Deploy code to production with features **turned off**; enable gradually via flags.

**How It Works:**

1. Deploy new code with feature flag disabled
2. Enable flag for internal users (dogfooding)
3. Enable flag for beta users
4. Enable flag for all users (full release)
5. Remove flag after full rollout

**Pros:**

- Decouple deployment from release
- Test in production with real data
- Instant rollback (toggle flag off)

**Cons:**

- Flag management overhead
- Technical debt (old flags)

**Example:**

```typescript
import { FeatureFlagService } from "./feature-flags";

export class EventService {
  constructor(
    private readonly repository: EventRepository,
    private readonly flags: FeatureFlagService,
  ) {}

  async createEvent(event: Event): Promise<Event> {
    // Feature flag controls promotion feature
    if (this.flags.isEnabled("event.promotion", event.userId)) {
      return this.createPromotedEvent(event);
    }
    return this.createStandardEvent(event);
  }
}
```

---

## Rollback Strategies

**Always have a rollback plan.** Every deployment should be reversible in <5 minutes.

### Fast Rollback Methods

| Method                         | Time to Rollback | Requirements                   |
| ------------------------------ | ---------------- | ------------------------------ |
| **Blue-Green flip**            | <1 minute        | Blue environment still running |
| **Feature flag toggle**        | <1 minute        | Feature behind flag            |
| **Previous container image**   | <5 minutes       | Kubernetes rollout undo        |
| **Previous artifact redeploy** | <10 minutes      | Artifact still available       |
| **Database rollback**          | <30 minutes      | Migrations are reversible      |

**Example Rollback Commands:**

```bash
# Kubernetes rollback to previous deployment
kubectl rollout undo deployment/backstage-backend

# Helm rollback to previous release
helm rollback backstage 1

# Feature flag toggle (via API)
curl -X POST https://flags.example.com/api/flags/event.promotion/disable
```

---

## Deployment Checklist

**Before Deployment:**

- [ ] Artifact built and tested in CI
- [ ] Database migrations tested and rolled back
- [ ] Feature flags configured
- [ ] Smoke tests ready
- [ ] Rollback plan documented
- [ ] Monitoring dashboards prepared

**During Deployment:**

- [ ] Run smoke tests after deployment
- [ ] Monitor error rates, latency, business metrics
- [ ] Verify logs for anomalies
- [ ] Check health endpoints

**After Deployment:**

- [ ] Confirm metrics stable for 15-30 minutes
- [ ] Verify critical user journeys work
- [ ] Update release notes
- [ ] Remove old artifacts (after retention period)

---

## Deployment Strategy Decision Tree

```
High risk change?
├─ Yes → Canary deployment (5% → 25% → 50% → 100%)
└─ No → Rolling deployment

Need instant rollback?
├─ Yes → Blue-Green deployment OR feature flag
└─ No → Rolling deployment

Large architectural change?
├─ Yes → Feature flag + canary deployment
└─ No → Rolling deployment

Database schema change?
├─ Yes → Expand-Contract pattern + rolling deployment
└─ No → Any strategy
```

---

## DORA Metrics Impact

| Strategy          | Deployment Frequency | Lead Time | MTTR                           |
| ----------------- | -------------------- | --------- | ------------------------------ |
| **Blue-Green**    | High                 | Low       | Very Low (<1 min rollback)     |
| **Canary**        | High                 | Low       | Low (automated rollback)       |
| **Rolling**       | High                 | Low       | Medium (redeploy for rollback) |
| **Feature Flags** | Very High            | Very Low  | Very Low (toggle off)          |

---

## Pre-Merge Checklist

- [ ] Deployment strategy selected based on risk
- [ ] Rollback plan documented and tested
- [ ] Database migrations backwards-compatible
- [ ] Smoke tests verify critical functionality
- [ ] Monitoring alerts configured
- [ ] Feature flags in place for high-risk changes
- [ ] Deployment automation tested in staging
- [ ] MTTR target <5 minutes for rollback

---

**Golden Rule:** If you can't roll back in <5 minutes, the deployment strategy is **too risky**.
