# Testing Pyramid & Risk-Driven Testing Strategy

> Balance speed, confidence, and cost with automated tests at multiple levels.

## Core Principle

**Test at the right level to get fast feedback on the risks that matter.** Use a pyramid shape: many unit tests, fewer integration tests, fewest E2E tests.

---

## Testing Pyramid

```
        /\
       /  \      E2E Tests (Fewest)
      /    \     - Full user journeys
     /------\    - Slowest, most brittle
    /        \
   /  Integ.  \  Integration Tests (Some)
  /   Tests    \ - Service boundaries
 /--------------\- Database, APIs, external services
/                \
/   Unit Tests    \ Unit Tests (Most)
/                  \ - Fast, focused, deterministic
--------------------
```

**Distribution Target:**

- **70%** Unit tests — Fast, isolated, deterministic
- **20%** Integration tests — Test boundaries and contracts
- **10%** E2E tests — Critical user journeys only

---

## Test Types & Purpose

### 1. Unit Tests

**Purpose:** Verify **single units** of code (functions, classes) in isolation.

**Characteristics:**

- Fast (<1 second per test)
- Deterministic (same input → same output)
- No external dependencies (mock/stub all I/O)
- High coverage of edge cases

**Example:**

```typescript
// Unit test for domain logic
describe("EventValidator", () => {
  it("should reject event with past date", () => {
    const pastDate = new Date("2020-01-01");
    const result = EventValidator.validate({ startDate: pastDate });

    expect(result.isValid).toBe(false);
    expect(result.errors).toContain("Start date must be in the future");
  });

  it("should accept event with future date", () => {
    const futureDate = new Date("2025-01-01");
    const result = EventValidator.validate({ startDate: futureDate });

    expect(result.isValid).toBe(true);
  });
});
```

---

### 2. Integration Tests

**Purpose:** Verify **interactions between components** (database, APIs, external services).

**Characteristics:**

- Slower (seconds per test)
- Test real boundaries (database, HTTP, file system)
- Use test databases or containers
- Verify contract adherence

**Example:**

```typescript
// Integration test for repository
describe("EventRepository (Integration)", () => {
  let db: Knex;
  let repository: EventRepository;

  beforeEach(async () => {
    db = await createTestDatabase();
    await db.migrate.latest();
    repository = new EventRepository(db);
  });

  afterEach(async () => {
    await db.destroy();
  });

  it("should persist and retrieve event", async () => {
    const event = { title: "Test Event", startDate: new Date("2025-01-01") };

    const created = await repository.create(event);
    const retrieved = await repository.findById(created.id);

    expect(retrieved).toMatchObject(event);
  });
});
```

---

### 3. Contract Tests

**Purpose:** Verify **consumer-provider agreements** remain stable.

**Characteristics:**

- Test API contracts (request/response formats)
- Run on both consumer and provider side
- Catch breaking changes early
- Use tools like Pact or custom validators

**Example:**

```typescript
// Consumer contract test
describe("Event API Consumer Contract", () => {
  it("should match expected event response format", async () => {
    const mockResponse = {
      id: 123,
      title: "Test Event",
      startDate: "2025-01-01T10:00:00Z",
      location: "Room A",
    };

    const contract = z.object({
      id: z.number(),
      title: z.string(),
      startDate: z.string().datetime(),
      location: z.string(),
    });

    expect(() => contract.parse(mockResponse)).not.toThrow();
  });
});
```

---

### 4. E2E Tests

**Purpose:** Verify **critical user journeys** through the entire system.

**Characteristics:**

- Slowest (30s-2min per test)
- Most brittle (UI changes break tests)
- Test only **golden paths** and **critical flows**
- Run in production-like environment

**Example:**

```typescript
// E2E test (Playwright)
test("User can create and view event", async ({ page }) => {
  // Navigate to events page
  await page.goto("http://localhost:3000/events");

  // Create new event
  await page.click("text=Create Event");
  await page.fill('input[name="title"]', "DevOps Workshop");
  await page.fill('input[name="location"]', "Building A");
  await page.click('button:has-text("Save")');

  // Verify event appears in list
  await expect(page.locator("text=DevOps Workshop")).toBeVisible();
});
```

---

## Risk-Driven Testing

**Pattern:** Focus testing effort on **high-risk areas** based on business impact and change frequency.

**Risk Assessment Matrix:**

| Risk Level   | Characteristics                          | Testing Strategy                    |
| ------------ | ---------------------------------------- | ----------------------------------- |
| **Critical** | High business impact + frequent changes  | Unit + Integration + Contract + E2E |
| **High**     | High business impact OR frequent changes | Unit + Integration + Contract       |
| **Medium**   | Moderate impact + moderate changes       | Unit + Integration                  |
| **Low**      | Low impact + infrequent changes          | Unit only                           |

**Example:**

- **Critical**: Payment processing, user authentication
- **High**: Event creation, mentor matching
- **Medium**: Profile editing, search filters
- **Low**: Static pages, documentation

---

## Test Debt Management

**Anti-Patterns:**

- Flaky tests that fail intermittently
- Slow tests that block CI pipeline
- Over-mocking that doesn't test real behavior
- Brittle E2E tests that break on minor UI changes

**Remediation:**

- **Quarantine** flaky tests until fixed
- **Optimize** slow tests (run in parallel, use smaller datasets)
- **Replace** over-mocked tests with integration tests
- **Reduce** E2E tests to only critical paths

---

## Test Coverage Targets

| Test Type       | Coverage Target                              | Max Duration      |
| --------------- | -------------------------------------------- | ----------------- |
| **Unit**        | 80%+ for business logic, 60%+ overall        | <10 seconds total |
| **Integration** | Critical boundaries (repositories, gateways) | <30 seconds total |
| **Contract**    | All API endpoints (consumer + provider)      | <1 minute total   |
| **E2E**         | 3-5 critical user journeys                   | <5 minutes total  |

---

## Test Execution Strategy

**Local Development:**

```bash
yarn test --no-watch       # Unit tests (fast feedback)
yarn test:integration      # Integration tests (before commit)
yarn test:contract         # Contract tests (before commit)
```

**CI Pipeline:**

```yaml
# Run in parallel for speed
jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - run: yarn test --no-watch

  integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
    steps:
      - run: yarn test:integration

  e2e:
    runs-on: ubuntu-latest
    steps:
      - run: yarn test:e2e
```

---

## Pre-Merge Checklist

- [ ] Unit tests cover business logic (80%+ target)
- [ ] Integration tests cover database and API boundaries
- [ ] Contract tests verify API request/response formats
- [ ] E2E tests cover 3-5 critical user journeys
- [ ] All tests are deterministic (no flaky tests)
- [ ] Tests run in <10 minutes total
- [ ] Test pyramid maintained (70% unit, 20% integration, 10% E2E)
- [ ] High-risk areas have multiple test levels

---

**Golden Rule:** If a test is slow, flaky, or doesn't catch real bugs, **remove or replace it**.
