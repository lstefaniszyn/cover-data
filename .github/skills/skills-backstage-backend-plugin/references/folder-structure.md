# Folder Structure

> Standard folder structure for Backstage backend plugins with Clean Architecture.

## Directory Tree

```
plugins/[plugin-name]-backend/
├── src/
│   ├── constants/        # Organize by concern: domain/, database/, config/, api/
│   ├── database/         # Custom database client & connection pool management
│   ├── types/            # Domain & API types
│   ├── errors/           # Custom error classes
│   ├── domains/          # Domain behavior (pure functions)
│   ├── interfaces/       # Ports (repository/gateway interfaces)
│   ├── repositories/     # Data access implementations
│   ├── gateways/         # External service adapters (Catalog API, Auth, etc)
│   ├── services/         # Business logic orchestration
│   ├── controllers/      # HTTP handlers
│   ├── mappers/          # DTO mappers (optional for BFF)
│   ├── utils/            # Validation, response helpers, shared utilities
│   ├── config/           # Plugin-specific configuration
│   ├── router.ts         # Express router
│   ├── plugin.ts         # Backstage plugin entry
│   └── index.ts          # Public exports
├── migrations/           # Database migrations
├── techDocs/doc/
│   ├── ARCHITECTURE.md           # Plugin architecture & layer design
│   ├── API.md                    # API endpoints & error responses
│   ├── DATABASE.md               # Schema, migrations, queries
│   ├── SETUP.md                  # Configuration & deployment
│   └── *.md                      # Feature-specific docs
├── openapi.yaml          # API spec (write BEFORE code)
├── README.md             # Quick start (link to techDocs/doc/)
└── package.json
```

---

## Directory Descriptions

### `/src` - Source Code

#### `/constants`

**Purpose:** Eliminate magic strings/values; organize by concern.

**Pattern:** Subdirectories by concern (domain/, database/, config/, api/)

**Example:**

```
constants/
├── domain/
│   └── certification.constants.ts
├── database/
│   └── table-names.constants.ts
├── config/
│   └── default-values.constants.ts
└── api/
    └── endpoints.constants.ts
```

#### `/types`

**Purpose:** Define domain models, DTOs, and type contracts.

**Pattern:** Separate domain types from DTOs.

**Example:**

```
types/
├── track.types.ts           # Domain types
├── track-dto.types.ts       # Wire format
├── certification.types.ts
└── common.types.ts
```

#### `/errors`

**Purpose:** Custom error classes for domain-specific exceptions.

**Pattern:** One file per error type.

**Example:**

```
errors/
├── ValidationError.ts
├── NotFoundError.ts
├── UnauthorizedError.ts
├── ForbiddenError.ts
├── ConflictError.ts
├── DatabaseError.ts
└── GatewayError.ts
```

#### `/domains`

**Purpose:** Pure business logic without side effects or external dependencies.

**Pattern:** Top-level pure functions; verb/predicate naming.

**Example:**

```
domains/
├── track.ts                 # isTrackActive(), trackAppliesToEntity()
├── certification.ts         # canCertify(), isCertificationExpired()
└── level.ts                 # calculateProgress(), isLevelComplete()
```

**Imports Allowed:** types, constants, pure utils  
**Imports Forbidden:** framework code, DB clients, HTTP clients

#### `/interfaces`

**Purpose:** Define contracts (ports) for repositories and gateways.

**Pattern:** One interface file per port; I-prefix naming.

**Example:**

```
interfaces/
├── ITrackRepository.ts
├── ICatalogGateway.ts
└── ICertificationRepository.ts
```

#### `/repositories`

**Purpose:** Compose multiple data sources into validated domain objects.

**Pattern:** Implement port interface; inject DB + gateways + config.

**Example:**

```
repositories/
├── __tests__/
│   ├── TrackRepository.test.ts
│   └── TrackRepository.integration.test.ts
├── TrackRepository.ts
└── CertificationRepository.ts
```

#### `/gateways`

**Purpose:** Anti-corruption layer for external APIs.

**Pattern:** Implement port interface; validate responses; return DTOs.

**Example:**

```
gateways/
├── __tests__/
│   ├── CatalogGateway.test.ts
│   └── CatalogGateway.contract.test.ts
├── CatalogGateway.ts
└── AuthGateway.ts
```

#### `/services`

**Purpose:** Orchestrate domain operations using repositories.

**Pattern:** Inject repository interfaces; call domain functions.

**Example:**

```
services/
├── __tests__/
│   ├── TrackService.test.ts
│   └── TrackService.integration.test.ts
├── TrackService.ts
└── CertificationService.ts
```

#### `/controllers`

**Purpose:** Handle HTTP boundaries; validate input; orchestrate services.

**Pattern:** Extract request params; call service; return DTOs.

**Example:**

```
controllers/
├── __tests__/
│   └── TrackController.integration.test.ts
├── TrackController.ts
└── CertificationController.ts
```

#### `/mappers` (Optional)

**Purpose:** Transform domain objects into View Models for UI.

**Pattern:** Static methods for structural transformation.

**Example:**

```
mappers/
├── TrackMapper.ts
└── CertificationMapper.ts
```

#### `/utils`

**Purpose:** Shared utilities (validation, response helpers, etc).

**Example:**

```
utils/
├── error-mapper.ts          # mapErrorToHttp()
├── response-wrapper.ts      # wrapSuccess(), wrapError()
├── validation.ts            # validateEmail(), validateUrl()
└── date-utils.ts            # formatDate(), parseDate()
```

#### `/config`

**Purpose:** Plugin-specific configuration loading and validation.

**Example:**

```
config/
└── plugin-config.ts
```

---

### `/migrations` - Database Migrations

**Purpose:** Version-controlled database schema changes.

**Pattern:** Timestamp-prefixed files; up/down methods.

**Example:**

```
migrations/
├── 20240101000000_create_tracks.js
├── 20240102000000_add_levels.js
└── 20240103000000_add_certifications.js
```

---

### `/techDocs/doc` - Documentation

**Purpose:** Comprehensive plugin documentation.

**Required Files:**

- `ARCHITECTURE.md` - Plugin architecture & layer design
- `API.md` - API endpoints & error responses
- `DATABASE.md` - Schema, migrations, queries
- `SETUP.md` - Configuration & deployment

**Example:**

```
techDocs/doc/
├── ARCHITECTURE.md
├── API.md
├── DATABASE.md
├── SETUP.md
├── FEATURES.md
└── TROUBLESHOOTING.md
```

---

## Layer Rules

### Domain Layer (Pure TypeScript)

**Folders:** `types/`, `errors/`, `domains/`

**Rules:**

- MUST avoid framework imports
- MUST keep pure TypeScript
- NO `express`, `@backstage/*` runtime (type-only imports OK)
- NO `knex`, I/O libs, SDKs

### Application Layer (Orchestration)

**Folders:** `services/`, `interfaces/`, `controllers/`

**Rules:**

- MUST depend only on domain + ports
- Controllers handle HTTP validation & routing only
- Services orchestrate domain operations via repositories

### Infrastructure Layer (Side Effects)

**Folders:** `repositories/`, `gateways/`

**Rules:**

- MUST implement ports to reach external systems (DB, APIs, config)
- Repositories compose data sources into domain objects
- Gateways validate external responses and return DTOs

---

## Test Locations

Tests are **colocated** within `src/[layer]/__tests__/` subdirectories.

**Pattern:**

- `__tests__/[Module].test.ts` - Unit tests
- `__tests__/[Module].integration.test.ts` - Integration tests
- `__tests__/[Module].contract.test.ts` - Contract tests
- `__tests__/[Module].smoke.test.ts` - E2E tests

**Example:**

```
src/services/
├── __tests__/
│   ├── TrackService.test.ts                    # Unit
│   └── TrackService.integration.test.ts        # Integration
└── TrackService.ts
```

---

## Naming Conventions

| Element                 | Convention                     | Examples                                       |
| ----------------------- | ------------------------------ | ---------------------------------------------- |
| **Class filenames**     | PascalCase.ts                  | `CertificationService.ts`, `CatalogGateway.ts` |
| **Interface filenames** | I-prefix + PascalCase          | `ICatalogGateway.ts`, `ITrackRepository.ts`    |
| **Type filenames**      | kebab-case.ts                  | `track.types.ts`, `certification.types.ts`     |
| **Utility filenames**   | kebab-case.ts                  | `error-mapper.ts`, `response-wrapper.ts`       |
| **Test files**          | `[Module].test.ts`             | `TrackService.test.ts`                         |
| **Integration tests**   | `[Module].integration.test.ts` | `TrackService.integration.test.ts`             |

---

## Pre-Merge Checklist

- [ ] Folder structure follows Clean Architecture layers
- [ ] Domain layer has no framework imports
- [ ] Services depend only on repository interfaces
- [ ] Controllers are in separate layer from services
- [ ] Tests are colocated in `__tests__/` subdirectories
- [ ] Documentation exists in `techDocs/doc/`
- [ ] Migrations are in `migrations/` directory
- [ ] OpenAPI spec exists at root if plugin exposes HTTP API
