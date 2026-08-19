# Backend Testing Strategy

> Comprehensive testing strategy for Backstage backend plugins.

## Testing Pyramid

**Many unit → fewer integration → minimal E2E**

Tests MUST be deterministic and fast. Coverage: 80% overall, 90% domain/application.

---

## Tooling

- **Test Runner:** Jest
- **HTTP Tests:** supertest
- **Contract Tests:** @pact-foundation/pact (optional)
- **Property-based:** fast-check
- **Mutation testing:** @stryker-mutator/core on critical business modules
- **Coverage thresholds (CI gates):** overall >= 80%, domain/application >= 90%

---

## Test Type Matrix

| Type            | Scope                              | Location Pattern                                     | Requirements                                                                                                                                                                                                                                       | Key Assertions                                                               |
| --------------- | ---------------------------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **Unit**        | Domain/services/utils, no I/O      | `src/[layer]/__tests__/[Module].test.ts`             | • No DB/network/filesystem<br>• Inject collaborators via fakes/stubs/mocks<br>• <100ms execution<br>• Table-driven for transformations                                                                                                             | `expect(svc.getById()).rejects.toThrow(/not found/i)`                        |
| **Integration** | HTTP layer + real DB               | `src/[layer]/__tests__/[Module].integration.test.ts` | • Supertest against Express router<br>• Ephemeral DB (test containers/SQLite)<br>• **Idempotent setup/teardown:** `beforeEach` (reset state), `afterEach` (cleanup)<br>• Isolated test data (no shared state)<br>• Test DB transactions & rollback | `expect(res.status).toBe(200)`<br>`expect(res.body.data.name).toBeDefined()` |
| **Contract**    | API boundaries (provider/consumer) | `src/[layer]/__tests__/[Module].contract.test.ts`    | • **Provider:** Assert responses match OpenAPI/JSON schemas<br>• **Consumer:** Mock external APIs, validate DTO → domain mapping<br>• Store contracts as CI artifacts                                                                              | `expect(AjvValidator.validate(res.body, schema)).toBe(true)`                 |
| **E2E**         | Critical flows (2-5 max)           | `src/[layer]/__tests__/[Module].smoke.test.ts`       | • Production-like config<br>• Ephemeral infrastructure<br>• Health + read + write paths<br>• Auto-apply migrations                                                                                                                                 | `expect(res.body.status).toBe('ok')`                                         |
| **Migration**   | DB schema changes                  | Same as Integration                                  | • Apply migrations in sandbox DB<br>• Expand-and-contract patterns<br>• Test rollback paths                                                                                                                                                        | Schema assertions                                                            |
| **Performance** | Hot endpoints (IF >100 req/s)      | Same as Integration                                  | • Realistic payloads<br>• Benchmark list/search endpoints                                                                                                                                                                                          | Response time thresholds                                                     |
| **Resilience**  | Downstream failures                | Same as Integration                                  | • Inject timeouts/failures into ports<br>• Verify retries, circuit breaking<br>• Idempotent handlers                                                                                                                                               | Retry/fallback behavior                                                      |
| **Security**    | Auth/authz + input validation      | Same as Integration                                  | • Valid/expired/missing tokens<br>• Reject invalid params → 400<br>• No secrets logged<br>• Test authorization scopes                                                                                                                              | `expect(res.status).toBe(401)`                                               |

**Naming:** All tests end in `.test.ts`. Use prefix for type: `.integration.test.ts`, `.contract.test.ts`, `.smoke.test.ts`.

---

## Unit Tests

**Purpose:** Test pure logic and ports via fakes; no network/DB/FS.

**Key Principles:**

- Verify business rules, error mapping, and boundary conditions
- Keep tests fast (<100ms), deterministic, and focused
- Use table-driven tests for transformations, guards, and mappers

**Example:**

```ts
import { TrackService } from "../TrackService";
import type { ITrackRepository } from "../../interfaces/ITrackRepository";

describe("TrackService", () => {
  it("throws NotFoundError when repository returns null", async () => {
    const repo: jest.Mocked<ITrackRepository> = {
      findById: jest.fn().mockResolvedValue(null),
    };
    const svc = new TrackService(repo);
    await expect(svc.getById("track-001")).rejects.toThrow(/not found/i);
  });

  it("returns track when repository finds it", async () => {
    const mockTrack = { id: "track-001", name: "Test Track" };
    const repo: jest.Mocked<ITrackRepository> = {
      findById: jest.fn().mockResolvedValue(mockTrack),
    };
    const svc = new TrackService(repo);
    const result = await svc.getById("track-001");
    expect(result).toEqual(mockTrack);
  });
});
```

---

## Integration Tests

**Purpose:** Test HTTP layer + real DB.

**Key Principles:**

- Use **supertest** against Express router
- Ephemeral Postgres (test containers) or SQLite with migrations
- Validate status codes, response bodies, pagination, and error mapping
- Test real database interactions with isolated test data

**Example:**

```ts
import request from "supertest";
import { createRouter } from "../../router";

describe("GET /tracks/:id", () => {
  let app: express.Application;

  beforeEach(async () => {
    app = express();
    app.use(await createRouter({ logger: console as any, db: testDb }));
  });

  it("returns 200 with track data", async () => {
    const res = await request(app).get("/tracks/track-001");
    expect(res.status).toBe(200);
    expect(res.body.data.name).toBeDefined();
  });

  it("returns 404 for non-existent track", async () => {
    const res = await request(app).get("/tracks/non-existent");
    expect(res.status).toBe(404);
    expect(res.body.error.name).toBe("NotFoundError");
  });
});
```

---

## Test Isolation & Cleanup

**Pattern: Transaction Rollback (PostgreSQL, MySQL, SQLite)**

```ts
describe("TrackRepository", () => {
  let db: Knex;
  let trx: Knex.Transaction;

  beforeAll(async () => {
    db = await setupTestDatabase();
  });

  beforeEach(async () => {
    trx = await db.transaction(); // Isolated per test
  });

  afterEach(async () => {
    await trx.rollback(); // Atomic cleanup
  });

  it("should insert and fetch track", async () => {
    const repo = new TrackRepository(trx);
    await repo.insert({ id: 1, name: "Test" });
    expect(await repo.findById(1)).toMatchObject({ name: "Test" });
  });
});
```

**Rules:**

- MUST create a fresh transaction per test; inject `trx` (not `db`) into repositories
- MUST rollback in `afterEach` for atomic, fast cleanup (<5ms)
- MUST create shared reference data (enums, config) in `beforeAll` _outside_ transaction scope
- MUST create test-specific entities _within_ transactions (automatically cleaned by rollback)
- MUST verify DB supports rollback (PostgreSQL/MySQL/SQLite). Fallback: truncate or DB snapshots.

---

## Contract Tests

**Purpose:** Verify API boundaries match contracts (provider/consumer).

**Key Principles:**

- **Provider:** Assert responses match OpenAPI/JSON schemas
- **Consumer:** Mock external APIs, validate DTO → domain mapping
- Store contracts as CI artifacts

**Example:**

```ts
import request from "supertest";
import { AjvValidator } from "../../utils/AjvValidator";
import { tracksResponseSchema } from "../schemas";

describe("GET /tracks (Provider Contract)", () => {
  it("returns 200 with valid schema", async () => {
    const res = await request(app).get("/tracks");
    expect(res.status).toBe(200);
    expect(AjvValidator.validate(res.body, tracksResponseSchema)).toBe(true);
  });

  it("returns 404 with valid error schema", async () => {
    const res = await request(app).get("/tracks/non-existent");
    expect(res.status).toBe(404);
    expect(res.body.error.name).toBe("NotFoundError");
    expect(res.body.error.message).toBeDefined();
  });
});
```

---

## E2E / System Tests

**Purpose:** Smoke tests for critical flows (2-5 max).

**Key Principles:**

- Spin up service with test config
- Exercise critical flows with supertest
- Test production-like configuration with ephemeral infrastructure
- Focus on health checks, read paths, and write paths

**Example:**

```ts
import request from "supertest";
import { setupTestApp } from "../helpers/setup";

describe("E2E: Track Management", () => {
  let app: express.Application;

  beforeAll(async () => {
    app = await setupTestApp();
  });

  it("health check returns ok", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("ok");
  });

  it("can create and retrieve track", async () => {
    const createRes = await request(app).post("/tracks").send({ name: "Test Track", description: "E2E test" });

    expect(createRes.status).toBe(201);
    const trackId = createRes.body.data.id;

    const getRes = await request(app).get(`/tracks/${trackId}`);
    expect(getRes.status).toBe(200);
    expect(getRes.body.data.name).toBe("Test Track");
  });
});
```

---

## Performance Tests

**Purpose:** Benchmark hot endpoints (>100 req/s or complex queries).

**Key Principles:**

- Use realistic payloads
- Test list/search endpoints
- Set response time thresholds

**Example:**

```ts
describe("Performance: GET /tracks", () => {
  it("responds within 200ms for 100 tracks", async () => {
    const start = Date.now();
    const res = await request(app).get("/tracks?limit=100");
    const duration = Date.now() - start;

    expect(res.status).toBe(200);
    expect(duration).toBeLessThan(200);
  });
});
```

---

## Security Tests

**Purpose:** Test auth/authz + input validation.

**Key Principles:**

- Valid/expired/missing tokens
- Reject invalid parameters → 400
- No secrets logged
- Test authorization scopes

**Example:**

```ts
describe("Security: Authentication", () => {
  it("returns 401 for missing auth token", async () => {
    const res = await request(app).get("/tracks");
    expect(res.status).toBe(401);
  });

  it("returns 403 for insufficient permissions", async () => {
    const res = await request(app).delete("/tracks/track-001").set("Authorization", "Bearer read-only-token");
    expect(res.status).toBe(403);
  });
});

describe("Security: Input Validation", () => {
  it("rejects invalid track ID", async () => {
    const res = await request(app).get("/tracks/invalid-id!@#");
    expect(res.status).toBe(400);
    expect(res.body.error.name).toBe("ValidationError");
  });
});
```

---

## CI Integration & Gates

- Run unit+integration on every PR
- Contract/provider verification on main or nightly
- Fail pipeline on coverage or mutation score regression
- Publish coverage & test reports
- Retain logs for flaky analysis

---

## Test Selection Guide

```
Need to test...
│
├─ Pure business logic? → Unit Test
│   └─ Fast, no I/O, inject fakes
│
├─ HTTP endpoint? → Integration Test
│   └─ supertest + ephemeral DB
│
├─ API contract? → Contract Test
│   └─ Validate schemas, DTOs
│
├─ Critical flow? → E2E Test
│   └─ 2-5 smoke tests only
│
└─ Auth/input validation? → Security Test
    └─ 401/403/400 scenarios
```

---

## Pre-Merge Checklist

- [ ] Unit tests for domain/services (no I/O)
- [ ] Integration tests for HTTP + DB
- [ ] Contract tests if public API
- [ ] E2E tests for critical flows (2-5 max)
- [ ] Security tests for auth + validation
- [ ] Coverage >= 80% overall, >= 90% domain/application
- [ ] Tests are deterministic and fast
- [ ] Test isolation via transactions or cleanup
- [ ] Error paths covered (not just happy paths)
