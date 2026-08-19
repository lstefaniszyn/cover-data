# Observability & Operability Patterns

> Make systems understandable in production with structured logging, metrics, tracing, and health checks.

## Core Principle

**If you can't observe it, you can't operate it.** Every service must provide visibility into its state, behavior, and dependencies.

---

## Three Pillars of Observability

### 1. Logs (What happened?)

**Pattern:** Structured logs that are searchable, filterable, and correlatable.

**Rules:**

- Use **structured JSON** format (not plain text)
- Include **correlation IDs** to track requests across services
- Log at appropriate levels: DEBUG, INFO, WARN, ERROR
- Redact sensitive data (passwords, tokens, PII)
- Include context: service name, version, environment, timestamp

**Example:**

```typescript
import { Logger } from "@backstage/backend-plugin-api";

export class EventService {
  constructor(private readonly logger: Logger) {}

  async createEvent(event: Event, userId: string): Promise<Event> {
    const correlationId = generateCorrelationId();

    this.logger.info("Creating event", {
      correlationId,
      userId,
      eventTitle: event.title,
      eventDate: event.startDate,
    });

    try {
      const result = await this.repository.create(event);
      this.logger.info("Event created successfully", {
        correlationId,
        eventId: result.id,
      });
      return result;
    } catch (error) {
      this.logger.error("Failed to create event", {
        correlationId,
        error: error.message,
        stack: error.stack,
      });
      throw error;
    }
  }
}
```

---

### 2. Metrics (How much? How fast?)

**Pattern:** Time-series data that tracks system behavior over time.

**Key Metrics:**

- **RED metrics** (Requests, Errors, Duration)
- **USE metrics** (Utilization, Saturation, Errors)
- **Business metrics** (events created, users active, conversions)

**Example:**

```typescript
import { MetricsService } from "./metrics";

export class EventService {
  constructor(
    private readonly repository: EventRepository,
    private readonly metrics: MetricsService,
  ) {}

  async createEvent(event: Event): Promise<Event> {
    const startTime = Date.now();
    this.metrics.increment("event.create.requests");

    try {
      const result = await this.repository.create(event);
      const duration = Date.now() - startTime;

      this.metrics.increment("event.create.success");
      this.metrics.histogram("event.create.duration", duration);
      this.metrics.gauge("event.total_count", await this.repository.count());

      return result;
    } catch (error) {
      this.metrics.increment("event.create.errors");
      throw error;
    }
  }
}
```

---

### 3. Traces (Where did time go?)

**Pattern:** Distributed tracing to track requests across services.

**Rules:**

- Propagate trace IDs across service boundaries
- Instrument critical paths (API calls, database queries, external services)
- Use tools like OpenTelemetry, Jaeger, Zipkin

**Example:**

```typescript
import { trace, SpanStatusCode } from "@opentelemetry/api";

export class EventService {
  async createEvent(event: Event): Promise<Event> {
    const tracer = trace.getTracer("event-service");

    return tracer.startActiveSpan("createEvent", async (span) => {
      span.setAttribute("event.title", event.title);
      span.setAttribute("event.date", event.startDate.toISOString());

      try {
        const result = await this.repository.create(event);
        span.setStatus({ code: SpanStatusCode.OK });
        return result;
      } catch (error) {
        span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
        span.recordException(error);
        throw error;
      } finally {
        span.end();
      }
    });
  }
}
```

---

## Health Checks

**Pattern:** Provide `/health` and `/ready` endpoints for orchestrators.

**Types:**

1. **Liveness** (`/health`) — Is the service running?
2. **Readiness** (`/ready`) — Is the service ready to accept traffic?

**Example:**

```typescript
import { Router } from "express";

export function createHealthRouter(db: Knex): Router {
  const router = Router();

  // Liveness: Just respond (service is alive)
  router.get("/health", (req, res) => {
    res.json({ status: "ok" });
  });

  // Readiness: Check dependencies (database, cache, etc.)
  router.get("/ready", async (req, res) => {
    try {
      await db.raw("SELECT 1"); // Check database connection
      res.json({ status: "ready", checks: { database: "ok" } });
    } catch (error) {
      res.status(503).json({
        status: "not_ready",
        checks: { database: "failed" },
        error: error.message,
      });
    }
  });

  return router;
}
```

---

## Alerting Strategy

**Rules:**

- Alert on **symptoms** (user impact), not causes
- Use **SLOs** (Service Level Objectives) to define acceptable behavior
- Avoid alert fatigue (tune thresholds, reduce noise)
- Every alert must be **actionable**

**Example Alerts:**

```yaml
# CloudWatch alarms
ErrorRateHigh:
  metric: event.create.errors
  threshold: > 5% of requests
  duration: 5 minutes
  action: Page on-call engineer

ResponseTimeSlow:
  metric: event.create.duration.p95
  threshold: > 2 seconds
  duration: 10 minutes
  action: Notify team channel

DatabaseConnectionsLow:
  metric: database.connections.available
  threshold: < 10 connections
  duration: 5 minutes
  action: Auto-scale database OR page DBA
```

---

## Correlation IDs

**Pattern:** Track requests across services with unique IDs.

**Implementation:**

```typescript
import { Request, Response, NextFunction } from "express";
import { v4 as uuidv4 } from "uuid";

export function correlationIdMiddleware(req: Request, res: Response, next: NextFunction) {
  // Use existing correlation ID or generate new one
  const correlationId = req.headers["x-correlation-id"] || uuidv4();

  req.correlationId = correlationId;
  res.setHeader("x-correlation-id", correlationId);

  next();
}
```

---

## Metrics to Track

### RED Metrics (Request-focused)

| Metric       | Description                   | Target       |
| ------------ | ----------------------------- | ------------ |
| **Rate**     | Requests per second           | Track trends |
| **Errors**   | Error rate (% of requests)    | < 1%         |
| **Duration** | Response time (P50, P95, P99) | P95 < 500ms  |

### USE Metrics (Resource-focused)

| Metric          | Description                      | Target     |
| --------------- | -------------------------------- | ---------- |
| **Utilization** | CPU, memory, disk usage          | < 80%      |
| **Saturation**  | Queue depth, wait times          | < 10 items |
| **Errors**      | Resource errors (OOM, disk full) | 0          |

### Business Metrics

| Metric              | Description                | Target           |
| ------------------- | -------------------------- | ---------------- |
| **Events created**  | Total events per day       | Track growth     |
| **Active users**    | Daily active users         | Track engagement |
| **Conversion rate** | % of visitors who register | Track funnel     |

---

## Log Aggregation

**Tools:**

- **CloudWatch Logs** (AWS)
- **Azure Monitor** (Azure)
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Datadog**, **Splunk**, **New Relic**

**Example Query (CloudWatch Insights):**

```sql
fields @timestamp, correlationId, message, error
| filter level = "ERROR"
| filter service = "event-service"
| sort @timestamp desc
| limit 100
```

---

## Pre-Merge Checklist

- [ ] Structured logs with correlation IDs
- [ ] Metrics track RED (Rate, Errors, Duration)
- [ ] Health check endpoints (`/health`, `/ready`)
- [ ] Alerts configured for critical issues
- [ ] Sensitive data redacted from logs
- [ ] Tracing instrumented for critical paths
- [ ] Dashboards show key metrics (errors, latency, throughput)
- [ ] Logs aggregated to central service

---

**Golden Rule:** If you can't diagnose an issue in <5 minutes using logs/metrics/traces, **observability is insufficient**.
