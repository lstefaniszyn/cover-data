# Backend Architecture Layers

> Build Backstage backend plugins with **Clean Architecture** and **SOLID** principles using **ports & adapters** with clear layer separation.

## Core Principles

1. **Type Safety** — MUST NOT use `any` in domain or service layers; MAY use temporary `any` at gateway/repository boundaries; MUST narrow types before returning.
2. **Validation at Boundaries** — MUST validate at THREE distinct layers:
   - (1) Controllers validate HTTP structure (presence, type, required fields)
   - (2) Gateways validate external response shapes (type-narrow, check required fields, wrap errors)
   - (3) Repositories validate business rules (constraints, state transitions, domain invariants)
3. **Error Handling Expectations** — MUST perform exhaustive error handling; catch errors at boundaries, wrap in domain errors, and map to HTTP responses.
4. **Layer Separation** — Domain (pure logic) → Application (orchestration) → Infrastructure (side-effects, gateways, DB)
5. **Testability** — Domain & services MUST be testable via dependency injection; tests MUST use fakes/stubs/mocks for infrastructure ports (DB, APIs), not embed mocks in production code.
6. **Security** — MUST use parameterized queries; validate input at entry points

---

## Glossary

- **Adapter/Gateway**: Infrastructure anti-corruption layer calling external APIs and returning DTOs (untransformed wired data); handles protocol concerns (auth, HTTP, error wrapping) and structural validation (required fields, type-narrowing).
- **API Envelope**: Standardized HTTP response wrapper: `{ data: T, message?: string }` for success; `{ error: { name, message, details? } }` for errors.
- **Controller**: HTTP request handler validating input, calling services, and delegating to response wrapper for envelope formatting.
- **Domain Error**: Application-specific exception thrown at infrastructure boundaries, wrapped and mapped to HTTP status codes.
- **Domain Object**: Pure in-memory construct representing business concept with enforced business rules. Framework-independent, validated data structure enforcing business invariants.
- **Data Transfer Object (DTO)**: Serializable data structure (no business logic) for boundary crossing.
- **Mapper**: Optional pure transformer for DTO → View Model.
- **Port (Interface)**: Abstract contract a service depends on (repository, gateway) — implemented by infrastructure.
- **Repository**: Infrastructure component composing raw data sources (DB, gateways, config) into validated domain objects.
- **Service**: Application layer orchestrating domain objects via ports; contains business workflows only.
- **Validation Boundary**: First layer receiving external input where data MUST be checked.
- **View Model**: Optional flattened/filtered shape for UI (if Mapper is used).

---

## Layer Flow

```
Controllers (HTTP Layer)
   ↓
   Validate HTTP input
   Call services with validated data
   Map domain errors to HTTP responses
   ↓
Services (Domain Logic Orchestration)
   ↓
   Call repositories to get domain objects
   Implement business logic
   Orchestrate domain object workflows
   ↓
Repositories (Domain Object Construction)
   ↓
   Orchestrate data from multiple sources
   Call DB, gateways, config as needed
   Build and validate domain objects
   Wrap errors in domain types
   ↓
Infrastructure (Gateways, DB, Config)
   ↓
   Database access (Knex.js)
   External API calls (Gateways)
   Configuration loading
   Validate external API response shapes (DTOs)
```

---

## 1. Constants

**Purpose:** Eliminate magic strings/values; enable safe refactoring.

**Pattern:** Organize by concern (`domain/`, `database/`, `config/`, `api/`); use `as const satisfies Record<K, V>` for type safety.

**Rules:**

- MUST organize into subfolders or files by concern
- MUST use `as const satisfies Record<K, V>` pattern
- MUST avoid magic strings/numbers in code

**Example:**

```ts
export const CERTIFICATION_STATE = {
  PASSED: "passed",
  FAILED: "failed",
} as const satisfies Record<string, CertificationState>;
```

---

## 2. Types

**Purpose:** Define domain models, DTOs, and type contracts.

**Pattern:** Organize types by layer (domain, DTO, view models); keep files pure type declarations.

**Rules:**

- MUST separate domain types from DTOs
- MUST keep type files pure declarations

**Example:**

```ts
// types/track.types.ts (domain)
export interface Track {
  id: string;
  name: string;
  levels: Level[];
}

// types/track-dto.types.ts (wire format)
export interface TrackDto {
  id: string;
  name: string;
  levelCount: number;
}
```

### 2.1 API Response Envelope

**Purpose:** Standardize HTTP response format.

**Schema:**

```ts
// Success: { data: T, message?: string }
// Error: { error: { name: string, message: string, details?: unknown } }
```

**Rules:**

- MUST wrap all HTTP responses in envelope
- MUST use response wrapper utility

---

## 3. Domain Behavior

**Purpose:** Encapsulate pure business logic without side effects or external dependencies.

**Pattern:** Top-level pure functions in `domains/`; use classes only for constraint enforcement.

**Rules:**

- MUST implement as pure functions
- MUST use verb/predicate naming
- MUST separate types from logic
- MUST NOT import framework/infrastructure
- MUST NOT perform I/O or logging
- MAY use classes IF enforcing constraints
- MAY group functions IF >10 functions AND improves discoverability

**Example:**

```ts
// domains/track.ts
export function isTrackActive(track: Track): boolean {
  return !track.draft && track.levels.length > 0;
}

export function trackAppliesToEntity(track: Track, entityRef: string): boolean {
  return track.entities.includes(entityRef);
}
```

**Imports:**

- **Allowed:** types, constants, pure utils (`lodash`), Zod type inference only
- **Forbidden:** `express`, `@backstage/*` runtime, `knex`, I/O libs, SDKs

---

## 4. Services

**Purpose:** Orchestrate domain operations using validated domain objects from repositories.

**Pattern:** Inject repository interfaces via constructor; call domain functions; throw domain errors on failure.

**Rules:**

- MUST return domain object (validated entity)
- MUST depend ONLY on repository interfaces
- MUST validate business rules
- MUST throw domain errors on failure
- MUST implement one service per capability
- SHOULD use composition for complex workflows
- SHOULD log significant events
- MAY split services if >300 lines OR >5 methods OR multiple concerns

**Example:**

```ts
export class CertificationService {
  constructor(private readonly repo: ITrackRepository) {}

  async certifyEntity(entityRef: string): Promise<Certification> {
    const track = await this.repo.getById("default-track");
    if (!isTrackActive(track)) throw new ValidationError("track", "inactive");
    return this.repo.createCertification(entityRef, track.id);
  }
}
```

---

## 5. Repositories

**Purpose:** Compose multiple data sources (DB, gateways, config) into validated domain objects.

**Pattern:** Inject gateway ports + database + config; validate business rules; return domain objects.

**Rules:**

- MUST use parameterized queries
- MUST return domain object (not raw records/DTOs)
- MUST wrap errors in domain types
- MUST validate business rules
- SHOULD log operations
- MAY cache domain objects IF expensive/frequent (query cost >50ms OR >10 req/s)

**Gateway vs. Repository:**

| Aspect         | Gateway                          | Repository                                     |
| -------------- | -------------------------------- | ---------------------------------------------- |
| **Input**      | Raw external API response        | Gateway port + DB + config                     |
| **Output**     | DTO (type-narrowed)              | Domain Object (business rules enforced)        |
| **Validation** | Response shape (required fields) | Business rules (state transitions, invariants) |
| **Error**      | `GatewayError` → Repository      | Domain error → Service                         |

---

## 6. Gateways

**Purpose:** Anti-corruption layer for external APIs; validate response shapes, return DTOs.

**Pattern:** Implement port interface; validate external responses; wrap errors in `GatewayError`.

**Rules:**

- MUST implement port interface
- MUST use Backstage auth patterns
- MUST validate external response shapes
- MUST wrap errors in `GatewayError`
- MUST return DTO only (never domain objects)
- MAY use service-specific auth

**Example:**

```ts
export class CatalogGateway implements ICatalogGateway {
  async getEntity(ref: string): Promise<EntityDto> {
    try {
      const res = await this.http.get(`/entities/${ref}`);
      return res.data;
    } catch (err) {
      throw new GatewayError(`Failed to fetch entity ${ref}`, err instanceof Error ? err : new Error(String(err)));
    }
  }
}
```

---

## 7. Interfaces (Ports)

**Purpose:** Define contracts for repositories and gateways; enable loose coupling and testability.

**Pattern:** One interface per port; minimal method signatures.

**Rules:**

- MUST create one interface per port
- MUST keep method signatures minimal
- MUST follow I-prefix + PascalCase naming
- SHOULD limit to methods services actually need

**Example:**

```ts
export interface ITrackRepository {
  getById(id: string): Promise<Track | null>;
  createCertification(entityRef: string, trackId: string): Promise<Certification>;
}
```

---

## 8. Controllers

**Purpose:** Handle HTTP boundaries; validate input, orchestrate services, return DTOs.

**Pattern:** Extract request params/query/body; call service; map domain object to DTO; delegate envelope to Router.

**Rules:**

- MUST extract params, query, body
- MUST validate HTTP concerns only
- MUST call service methods
- MUST extract domain object to DTO
- MUST keep thin
- MUST map domain errors to HTTP codes
- MUST NOT apply envelope (Router handles this)

**Example:**

```ts
export class TrackController {
  constructor(private readonly svc: CertificationService) {}

  async certify(req: Request, res: Response): Promise<void> {
    const { entityRef } = req.params;
    if (!entityRef) throw new ValidationError("entityRef", "missing");
    const cert = await this.svc.certifyEntity(entityRef);
    res.json({ id: cert.id, status: cert.status }); // DTO extraction
  }
}
```

---

## 9. Mappers (Optional)

**Purpose:** Optional layer for flattening/filtering domain objects into UI-specific View Models.

**Pattern:** Static methods for pure structural transformation; Router invokes between controller and response wrapper.

**Rules:**

- SHOULD create one mapper per aggregate
- MUST use static methods
- MUST keep pure structural transformation
- MUST NOT branch on domain state
- MAY omit mapper entirely if API consumers use domain types

**When to Use:** BFF scenarios OR flattened/filtered shapes needed.

---

## 10. Router & Response Wrapper

**Purpose:** Wire dependencies, register routes, apply standardized HTTP envelope to all responses.

**Pattern:** Dependency injection → route registration → response wrapper.

**Rules:**

- MUST inject services/controllers/repos
- MUST register routes with controllers
- MUST use `express-promise-router`
- MUST ensure consistent wrapper usage
- MUST create wrapper utility in `utils/`
- MUST provide `wrapSuccess(data)` → envelope
- MUST provide `wrapError(error)` → envelope
- MUST invoke wrapper in route handlers
- MAY invoke Mapper before wrapper (§9)

**Request → Response Flow:**

1. Controller validates HTTP input, calls service, receives Domain Object
2. (Optional) IF Mapper exists: convert Domain Object → View Model
3. Response Wrapper applies envelope → HTTP response

**Envelope Format:** Success `{ data: T, message?: string }` | Error `{ error: { name, message, details? } }`

---

## Pre-Merge Checklist

- [ ] All tests pass (`yarn test --no-watch`)
- [ ] TypeScript compiles (`yarn tsc --noEmit`)
- [ ] Domain layer is pure TypeScript (no framework imports)
- [ ] Services depend only on repository interfaces
- [ ] Controllers validate HTTP input only
- [ ] Repositories return domain objects (not DTOs)
- [ ] Gateways return DTOs (not domain objects)
- [ ] All responses use API envelope
- [ ] Error handling at all boundaries
- [ ] Logging at layer transitions
