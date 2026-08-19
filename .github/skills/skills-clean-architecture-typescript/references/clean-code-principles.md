# Clean Code Principles

> Based on _Clean Code_ by Robert C. Martin. Optimize for readability, correctness, and long-term changeability.

## Core Objectives (follow in this order)

1. **Correctness** — the behavior is unambiguously right
2. **Clarity** — a competent peer can understand it quickly
3. **Simplicity** — the fewest moving parts to achieve the goal
4. **Cohesion** — each unit has a single responsibility
5. **Coupling** — dependencies are explicit and minimal
6. **Testability** — logic is easy to verify in isolation

---

## Naming

- Choose names that **reveal intent**; avoid abbreviations and encodings
- Use **pronounceable**, **searchable**, **consistent** vocabulary across the codebase
- Prefer **domain terms** over technical slang
- Functions/methods: verb or verb phrase; Classes/types: noun or noun phrase
- Booleans read as questions (**is**, **has**, **can**); Collections are pluralized
- Avoid overloading the same term for different concepts

**Examples:**

```ts
// ✅ Good
function calculateMonthlyPayment(principal: number, rate: number): number { ... }
interface UserProfile { ... }
const isActive = true;
const events: Event[] = [];

// ❌ Bad
function calc(p: number, r: number): number { ... }
interface IUser { ... }
const flag = true;
const data: Event[] = [];
```

---

## Functions & Methods

- Do **one thing** and do it well; if you can extract another responsibility, do it
- Keep them **small**; minimize branches and nesting
- Prefer **fewer parameters**; avoid flag parameters (they signal multiple responsibilities)
- No hidden side effects; return results rather than mutating external state
- Use meaningful defaults; keep parameter order consistent and logical
- Fail fast with clear messages when preconditions are not met

**Examples:**

```ts
// ✅ Good - Does one thing
function fetchUser(id: string): Promise<User> {
  return http.get(`/users/${id}`);
}

function validateUser(user: User): ValidationResult {
  // ...validation logic
}

// ❌ Bad - Does multiple things
function fetchAndValidateUser(id: string): Promise<ValidationResult> {
  const user = await http.get(`/users/${id}`);
  // ...validation logic mixed with fetching
}
```

**Parameter Guidelines:**

```ts
// ✅ Good - Few parameters
function createEvent(title: string, date: Date): Event { ... }

// ⚠️ Consider options object for >3 parameters
function createEvent(options: EventOptions): Event { ... }

// ❌ Bad - Flag parameter
function renderEvent(event: Event, isDetailed: boolean) { ... }

// ✅ Good - Separate functions
function renderEventSummary(event: Event) { ... }
function renderEventDetailed(event: Event) { ... }
```

---

## Comments

- Favor **self-explanatory code** over comments
- Write comments only when they **add value** that code cannot express (rationale, warnings, decisions)
- Keep comments **truthful** and **current**; delete misleading or obsolete comments
- Avoid noise ("obvious" restatements) and journal comments; use version control history instead

**Examples:**

```ts
// ❌ Bad - Obvious noise
// Get the user by ID
function getUserById(id: string): User { ... }

// ❌ Bad - Misleading/outdated
// Returns user profile (but actually returns full user object)
function fetchUser(id: string): User { ... }

// ✅ Good - Explains WHY
// Use exponential backoff to avoid overwhelming the API during outages
async function fetchWithRetry(url: string): Promise<Response> { ... }

// ✅ Good - Warning about gotcha
// Note: This mutates the original array for performance reasons
function sortInPlace(items: Item[]): Item[] { ... }
```

---

## Objects, Data, and State

- Prefer **immutable** data where practical; minimize shared mutable state
- Keep **invariants** obvious and enforced at boundaries
- Hide representation; expose **behavior** rather than getters/setters for every field
- Distinguish **core domain** objects from DTOs; avoid leaking one into the other
- Separate **construction** from **usage**; centralize complex creation

**Examples:**

```ts
// ✅ Good - Immutable
interface Event {
  readonly id: string;
  readonly title: string;
  readonly date: Date;
}

// ✅ Good - Behavior over getters/setters
class Track {
  isActive(): boolean {
    return !this.draft && this.levels.length > 0;
  }
}

// ❌ Bad - Anemic domain model
class Track {
  getDraft(): boolean {
    return this.draft;
  }
  getLevels(): Level[] {
    return this.levels;
  }
}
```

---

## Error Handling

- Treat errors as part of the design; model them explicitly
- Keep error paths **separate** from happy paths where it clarifies flow
- Provide **actionable** messages; include context, not secrets
- Don't return vague sentinel values; avoid swallowing errors
- Prefer **recovery at the right level**; propagate when a lower layer lacks context

**Examples:**

```ts
// ✅ Good - Explicit error types
class NotFoundError extends Error {
  constructor(
    public resourceType: string,
    public resourceId: string,
  ) {
    super(`${resourceType} with id "${resourceId}" not found`);
  }
}

// ✅ Good - Fail fast with context
function validateEmail(email: string): void {
  if (!email.includes("@")) {
    throw new ValidationError("email", email, "Email must contain @");
  }
}

// ❌ Bad - Swallow errors
try {
  await fetchData();
} catch (error) {
  // Silent failure
}

// ❌ Bad - Vague sentinel
function findUser(id: string): User | null {
  // Returns null for many reasons (not found, network error, etc.)
}

// ✅ Good - Explicit errors
async function findUser(id: string): Promise<User> {
  const user = await db.findById(id);
  if (!user) {
    throw new NotFoundError("User", id);
  }
  return user;
}
```

---

## Boundaries & Interfaces

- Define **clear contracts** between modules; fail loudly on contract violations
- Isolate third-party code behind **adapters/facades** to protect your domain
- Keep boundary objects **narrow** and **cohesive**; avoid "god interfaces"
- Prefer dependency inversion: depend on **abstractions**, not concretions
- Configuration and environment access are **edge concerns**; keep them at the perimeter

**Examples:**

```ts
// ✅ Good - Narrow interface (port)
interface IEventRepository {
  findById(id: string): Promise<Event | null>;
  save(event: Event): Promise<void>;
}

// ❌ Bad - God interface
interface IRepository {
  findById(id: string): Promise<any>;
  save(data: any): Promise<void>;
  delete(id: string): Promise<void>;
  query(sql: string): Promise<any>;
  backup(): Promise<void>;
  // ... 20 more methods
}

// ✅ Good - Adapter for third-party code
class CatalogGateway implements ICatalogGateway {
  constructor(private httpClient: HttpClient) {}

  async getEntity(ref: string): Promise<EntityDto> {
    // Isolate third-party API details
    const response = await this.httpClient.get(`/entities/${ref}`);
    return this.mapToDto(response.data);
  }
}
```

---

## Classes & Modules

- High **cohesion**: group responsibilities that change for the same reason
- Low **coupling**: minimize knowledge of other modules
- Small public surface; keep implementation details private
- Prefer **composition** over inheritance; inherit only for true is-a relationships
- Avoid static/global state; prefer explicit lifecycles and injection

**Examples:**

```ts
// ✅ Good - High cohesion (single responsibility)
class EventService {
  constructor(private repo: IEventRepository) {}

  async createEvent(data: EventData): Promise<Event> {
    // Business logic for event creation
  }
}

// ✅ Good - Composition over inheritance
class EventNotifier {
  constructor(
    private emailService: IEmailService,
    private slackService: ISlackService,
  ) {}

  async notifyAll(event: Event): Promise<void> {
    await Promise.all([
      this.emailService.send(event),
      this.slackService.send(event),
    ]);
  }
}

// ❌ Bad - God class (low cohesion)
class EventManager {
  createEvent() { ... }
  deleteEvent() { ... }
  sendEmail() { ... }
  logToDatabase() { ... }
  generateReport() { ... }
}
```

---

## Formatting & Structure

- Organize for **reading**: top-level policy first, details later
- One level of abstraction per function; don't mix policy with plumbing
- Consistent file layout: imports, types, public API, private details
- Keep files and directories **focused**; avoid "misc" catch-alls

**File Structure Example:**

```ts
// 1. Imports (grouped: external, internal, types)
import { Request, Response } from 'express';
import { EventService } from '../services/EventService';
import type { Event } from '../types/event.types';

// 2. Types/interfaces
interface EventControllerOptions { ... }

// 3. Public API
export class EventController {
  // Public methods first
  async create(req: Request, res: Response): Promise<void> { ... }
  async update(req: Request, res: Response): Promise<void> { ... }

  // Private methods last
  private validate(data: unknown): EventData { ... }
  private mapToDto(event: Event): EventDto { ... }
}
```

---

## Tests

- Tests are **first-class**: fast, deterministic, isolated
- Use tests to **drive design** toward small, decoupled units
- Cover both **happy paths** and **edge/failure** scenarios
- Name tests by behavior and intent; one assertion concept per test
- Avoid brittle tests; assert **observable outcomes**, not internals
- Keep **test data** obvious and minimal; prefer builders/fixtures over duplication

**Examples:**

```ts
// ✅ Good - Clear intent, single concept
describe("EventService", () => {
  it("throws NotFoundError when event does not exist", async () => {
    const repo = { findById: jest.fn().mockResolvedValue(null) };
    const service = new EventService(repo);

    await expect(service.getById("event-123")).rejects.toThrow(NotFoundError);
  });
});

// ❌ Bad - Testing internals, unclear intent
it("test event service", () => {
  // ...100 lines of setup
  expect(service.repo).toBeDefined();
  expect(service.logger).toBeDefined();
  // ...tests internal state instead of behavior
});
```

---

## Code Smells (Watch For These)

- Long functions, large classes, deeply nested conditionals
- Feature envy, data clumps, primitive obsession
- Divergent change (one module changes for many reasons)
- Shotgun surgery (one change touching many modules)
- Law of Demeter violations (train-wreck calls: `a.getB().getC().doSomething()`)
- Boolean flag parameters and ambiguous nulls
- Overuse of comments to compensate for unclear code

---

## Pre-Merge Checklist

- [ ] Names reveal intent; no cryptic abbreviations
- [ ] Functions do one thing; no flag parameters
- [ ] Comments explain WHY, not WHAT
- [ ] Errors are explicit and actionable
- [ ] Classes have single responsibility
- [ ] Composition over inheritance
- [ ] Tests are fast, deterministic, and isolated
- [ ] No god classes or god interfaces
- [ ] Consistent formatting and file structure

---

**Golden Rule:** Code is read far more often than it is written. Optimize for the reader.
