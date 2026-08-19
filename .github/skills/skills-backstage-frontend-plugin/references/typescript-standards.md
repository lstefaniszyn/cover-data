# TypeScript Development Standards

> These instructions assume TypeScript 5.x (or newer) compiling to ES2022 JavaScript baseline.

## Core Intent

- Respect the existing architecture and coding standards
- Prefer readable, explicit solutions over clever shortcuts
- Extend current abstractions before inventing new ones
- Prioritize maintainability and clarity, short methods and classes, clean code

---

## General Guardrails

- Target TypeScript 5.x / ES2022 and prefer native features over polyfills
- Use pure ES modules; never emit `require`, `module.exports`, or CommonJS helpers
- Rely on the project's build, lint, and test scripts unless asked otherwise
- Note design trade-offs when intent is not obvious

---

## Project Organization

- Follow the repository's folder and responsibility layout for new code
- Use **kebab-case filenames** (e.g., `user-session.ts`, `data-service.ts`) unless told otherwise
- Keep tests, types, and helpers near their implementation when it aids discovery
- Reuse or extend shared utilities before adding new ones

---

## Naming & Style

- Use **PascalCase** for classes, interfaces, enums, and type aliases
- Use **camelCase** for everything else (variables, functions, methods)
- Skip interface prefixes like `I`; rely on descriptive names
- Name things for their behavior or domain meaning, not implementation

**Examples:**

```ts
// ✅ Good
interface UserProfile { ... }
class EventService { ... }
function calculateDiscount() { ... }

// ❌ Bad
interface IUserProfile { ... }
class EventServiceImpl { ... }
function calc() { ... }
```

---

## Formatting & Style

- Run the repository's lint/format scripts (e.g., `npm run lint`) before submitting
- Match the project's indentation, quote style, and trailing comma rules
- Keep functions focused; extract helpers when logic branches grow
- Favor immutable data and pure functions when practical

---

## Type System Expectations

### Avoid `any`

```ts
// ❌ Bad
function processData(data: any) { ... }

// ✅ Good
function processData<T>(data: T) { ... }
// or
function processData(data: unknown) {
  if (typeof data === 'string') {
    // Type narrowed to string
  }
}
```

### Use Discriminated Unions

```ts
// ✅ Good
type LoadingState = { status: 'loading' };
type SuccessState = { status: 'success'; data: Event[] };
type ErrorState = { status: 'error'; error: string };

type EventState = LoadingState | SuccessState | ErrorState;

function render(state: EventState) {
  switch (state.status) {
    case 'loading':
      return <Spinner />;
    case 'success':
      return <EventList events={state.data} />;
    case 'error':
      return <Error message={state.error} />;
  }
}
```

### Centralize Shared Contracts

```ts
// types/event.ts
export interface Event {
  readonly id: string;
  readonly title: string;
  readonly summary?: string;
}

// components/EventCard.tsx
import type { Event } from "../types/event";
```

### Use TypeScript Utility Types

```ts
type ReadonlyEvent = Readonly<Event>;
type PartialEvent = Partial<Event>;
type EventRecord = Record<string, Event>;
type EventKeys = keyof Event;
```

---

## Async, Events & Error Handling

### Use `async/await`

```ts
// ✅ Good
async function fetchEvents() {
  try {
    const response = await fetch("/api/events");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    logger.error("Failed to fetch events", error);
    throw error;
  }
}
```

### Guard Edge Cases Early

```ts
// ✅ Good
function processEvent(event: Event | null) {
  if (!event) {
    return;
  }
  // Main logic here
}

// ❌ Bad
function processEvent(event: Event | null) {
  if (event) {
    // Deep nesting
  }
}
```

---

## Architecture & Patterns

### Single Responsibility

```ts
// ✅ Good - Separate concerns
class EventService {
  async fetchEvents() { ... }
}

class EventValidator {
  validate(event: Event) { ... }
}

// ❌ Bad - Mixed concerns
class EventManager {
  async fetchEvents() { ... }
  validate(event: Event) { ... }
  render(event: Event) { ... }
}
```

### Dependency Injection

```ts
// ✅ Good
class EventService {
  constructor(private apiClient: ApiClient) {}

  async fetchEvents() {
    return this.apiClient.get("/events");
  }
}

// ❌ Bad
class EventService {
  async fetchEvents() {
    const client = new ApiClient(); // Hard-coded dependency
    return client.get("/events");
  }
}
```

---

## External Integrations

- Instantiate clients outside hot paths and inject them for testability
- Never hardcode secrets; load them from secure sources
- Apply retries, backoff, and cancellation to network or IO calls
- Normalize external responses and map errors to domain shapes

```ts
// ✅ Good
class ApiClient {
  constructor(
    private baseUrl: string,
    private apiKey: string,
  ) {}

  async get(path: string) {
    const response = await fetch(`${this.baseUrl}${path}`, {
      headers: { Authorization: `Bearer ${this.apiKey}` },
    });

    if (!response.ok) {
      throw new ApiError(`HTTP ${response.status}`, response.statusText);
    }

    return response.json();
  }
}
```

---

## Security Practices

- Validate and sanitize external input with schema validators or type guards
- Avoid dynamic code execution and untrusted template rendering
- Encode untrusted content before rendering HTML; use framework escaping
- Use parameterized queries or prepared statements to block injection
- Keep secrets in secure storage, rotate them regularly, and request least-privilege scopes
- Use vetted crypto libraries only
- Patch dependencies promptly and monitor advisories

---

## Configuration & Secrets

- Reach configuration through shared helpers and validate with schemas
- Handle secrets via the project's secure storage; guard `undefined` and error states
- Document new configuration keys and update related tests

```ts
// ✅ Good
import { config } from "./config";

const apiKey = config.get("API_KEY");
if (!apiKey) {
  throw new Error("API_KEY not configured");
}
```

---

## UI & UX Components

- Sanitize user or external content before rendering
- Keep UI layers thin; push heavy logic to services or state managers
- Use messaging or events to decouple UI from business logic

```tsx
// ✅ Good
const EventCard = ({ event, onSelect }: EventCardProps) => {
  return (
    <Card onClick={() => onSelect(event.id)}>
      <Typography>{event.title}</Typography>
    </Card>
  );
};

// ❌ Bad
const EventCard = ({ event }: EventCardProps) => {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    await fetch("/api/events/" + event.id); // API call in component
    setLoading(false);
  };

  return <Card onClick={handleClick}>...</Card>;
};
```

---

## Testing Expectations

- Add or update unit tests with the project's framework and naming style
- Expand integration or end-to-end suites when behavior crosses modules
- Run targeted test scripts for quick feedback before submitting
- Avoid brittle timing assertions; prefer fake timers or injected clocks

```ts
// ✅ Good
test("fetchEvents returns events", async () => {
  const apiClient = new MockApiClient();
  apiClient.get.mockResolvedValue({ items: [mockEvent] });

  const service = new EventService(apiClient);
  const events = await service.fetchEvents();

  expect(events).toEqual([mockEvent]);
});
```

---

## Performance & Reliability

- Lazy-load heavy dependencies and dispose them when done
- Defer expensive work until users need it
- Batch or debounce high-frequency events to reduce thrash
- Track resource lifetimes to prevent leaks

```tsx
// ✅ Good - Lazy load heavy component
const HeavyComponent = React.lazy(() => import("./HeavyComponent"));

const App = () => (
  <Suspense fallback={<Spinner />}>
    <HeavyComponent />
  </Suspense>
);
```

---

## Documentation & Comments

- Add JSDoc to public APIs; include `@remarks` or `@example` when helpful
- Write comments that capture intent, and remove stale notes during refactors
- Update architecture or design docs when introducing significant patterns

````ts
/**
 * Fetches events from the API with optional filtering.
 *
 * @param filters - Optional filters to apply
 * @returns Promise resolving to array of events
 * @throws {ApiError} When API request fails
 *
 * @example
 * ```ts
 * const events = await fetchEvents({ status: 'published' });
 * ```
 */
async function fetchEvents(filters?: EventFilters): Promise<Event[]> {
  // ...
}
````

---

## Validation & Verification

- **Build:** `yarn tsc --noEmit` to check for type errors
- **Linting:** `yarn lint` to verify code style and patterns
- **Testing:** `yarn test --no-watch` to run unit and integration tests before submitting

---

## Pre-Merge Checklist

- [ ] TypeScript compiles with no errors (`yarn tsc --noEmit`)
- [ ] Linting passes (`yarn lint`)
- [ ] Tests pass (`yarn test --no-watch`)
- [ ] No `any` types (use `unknown` + type guards)
- [ ] Proper type imports (`import type { ... }`)
- [ ] JSDoc added to public APIs
- [ ] Error handling in place for async operations
