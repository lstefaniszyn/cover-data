---
name: skills-backstage-backend-plugin
description: Build Backstage backend plugins with Clean Architecture, TypeScript, Express, Knex/PostgreSQL, and comprehensive testing. Use when (1) Creating or modifying Backstage backend plugins, (2) Implementing Clean Architecture layers (Domain, Service, Repository, Controller), (3) Working with databases using Knex and migrations, (4) Integrating external APIs via Gateways, (5) Testing backend services (unit, integration, contract, E2E), (6) Using MCP tools for documentation and database exploration, (7) Setting up health checks and observability.
---

# Backstage Backend Plugin Development

## Platform Context

- **Primary managed database target:** Azure Database for PostgreSQL Flexible Server
- **Design implication:** Use PostgreSQL-compatible SQL, but avoid assumptions that require superuser-level control
- **Schema implication:** Treat relational tables + semi-structured JSON/JSONB as a first-class pattern

## Quick Start

- **Architecture:** Domain (pure logic) → Service (orchestration) → Repository (data) → Infrastructure (DB/API)
- **Validation:** HTTP input (Controllers) → External APIs (Gateways) → Business rules (Repositories)
- **Database:** Knex query builder with Backstage DatabaseService
- **Testing:** Unit (domain/services) → Integration (HTTP+DB) → Contract (API schemas) → E2E (smoke tests)
- **Documentation:** Use MCP tools for up-to-date API docs and DB exploration

## Architecture Decision Tree

```
1. Is it pure business logic with no side effects?
   → YES → Domain (src/domains/)

2. Does it orchestrate domain logic using repositories?
   → YES → Service (src/services/)

3. Does it compose data from DB/gateways/config into domain objects?
   → YES → Repository (src/repositories/)

4. Does it call external APIs and return DTOs?
   → YES → Gateway (src/gateways/)

5. Does it handle HTTP requests and map errors?
   → YES → Controller (src/controllers/)
```

[See references/architecture-layers.md for detailed layer definitions]

## Folder Structure

```
plugins/[plugin-name]-backend/
├── src/
│   ├── constants/        # Domain, database, config, API constants
│   ├── types/            # Domain types, DTOs, view models
│   ├── errors/           # Custom error classes mapped to HTTP
│   ├── domains/          # Pure business logic (no I/O)
│   ├── interfaces/       # Port interfaces (repositories, gateways)
│   ├── repositories/     # Data access (DB + gateways → domain objects)
│   ├── gateways/         # External API adapters (return DTOs)
│   ├── services/         # Business orchestration (use repositories)
│   ├── controllers/      # HTTP handlers (validate, call services)
│   ├── mappers/          # DTO transformations (optional)
│   ├── utils/            # Validation, response helpers
│   ├── config/           # Plugin-specific configuration
│   ├── router.ts         # Express router setup
│   ├── plugin.ts         # Backstage plugin entry
│   └── index.ts          # Public exports
├── techDocs/doc/
│   ├── ARCHITECTURE.md   # Plugin architecture & layer design
│   ├── API.md            # Endpoints, request/response schemas
│   ├── DATABASE.md       # Schema, migrations, queries
│   └── SETUP.md          # Configuration, deployment
├── openapi.yaml          # API specification (write BEFORE code)
└── README.md             # Quick start (links to techDocs/)
```

## Error Handling

### Error Types & HTTP Mapping

| Error Class         | When to Throw                    | HTTP Status |
| ------------------- | -------------------------------- | ----------- |
| `ValidationError`   | Input validation fails           | 400         |
| `UnauthorizedError` | Auth missing/invalid             | 401         |
| `ForbiddenError`    | Authorization check fails        | 403         |
| `NotFoundError`     | Resource not found               | 404         |
| `ConflictError`     | State conflict (duplicate, etc.) | 409         |
| `DatabaseError`     | DB operation fails               | 500         |
| `GatewayError`      | External API call fails          | 502/503     |

**Pattern:**

1. Catch at infrastructure boundaries (repository, gateway)
2. Wrap in domain error types
3. Map to HTTP status in controllers
4. Apply envelope in router

[See references/error-handling.md for detailed patterns]

## Database Integration

### Knex Query Builder with Backstage

```typescript
// Inject via coreServices.database
export class TrackRepository implements ITrackRepository {
  constructor(
    private readonly db: Knex,
    private readonly logger: LoggerService,
  ) {}

  async findById(id: string): Promise<Track | null> {
    const row = await this.db("tracks").where({ id }).first();

    if (!row) return null;
    return this.toDomain(row);
  }

  async create(track: Track): Promise<void> {
    await this.db("tracks").insert(this.toRow(track));
  }
}
```

**Key Principles:**

- Use parameterized queries (NO string concatenation)
- Register health checks via `coreServices.rootHealth`
- Extract plugin-specific config from `backend.database.plugin.<plugin-id>`
- Apply migrations before plugin starts

### Azure PostgreSQL Flexible + Semi-Structured Data Rules

- Prefer `jsonb` for semi-structured columns that will be queried (`metadata`, `attributes`, `contacts`, etc.)
- Keep critical filter/sort fields as typed scalar columns even if duplicated in JSON/JSONB
- Add indexes for real query paths (BTREE for scalar columns, GIN for JSONB containment/search)
- Use explicit JSON text extraction when applying string functions (`->>`, `#>>`, or `::text`)
- Do not apply `LOWER()` or `LIKE` directly to JSONB values without extracting/casting
- Avoid migration strategies that require superuser-only capabilities; keep migrations portable and explicit
- Document every JSON/JSONB field contract in techDocs DATABASE.md: shape, defaults, indexes, and query usage

**Example (important):**

```ts
// BAD: contacts is jsonb, LOWER(jsonb) fails in PostgreSQL
query.whereRaw("LOWER(COALESCE(contacts, ?)) LIKE ?", ["", `%${poc.toLowerCase()}%`]);

// GOOD: cast jsonb to text (or extract specific keys) before string matching
query.whereRaw("contacts::text ILIKE ?", [`%${poc}%`]);
```

[See references/database-patterns.md for migrations, health checks, and transaction handling]

## Testing Strategy

### Testing Pyramid

```
      △ E2E (2-5 smoke tests)
     ███
    █████ Contract (API schemas)
   ███████
  █████████ Integration (HTTP + DB)
 ███████████
█████████████ Unit (domain, services)
```

**Coverage Targets:** 80% overall, 90% domain/application

### Test Types

| Type            | Scope                         | Speed  | Dependencies             |
| --------------- | ----------------------------- | ------ | ------------------------ |
| **Unit**        | Domain, services, utils       | <100ms | None (fakes/stubs)       |
| **Integration** | Controllers, repositories, DB | <1s    | Test DB                  |
| **Contract**    | API boundaries                | <500ms | Mock external APIs       |
| **E2E**         | Critical flows                | <60s   | Ephemeral infrastructure |

[See references/testing-strategy.md for comprehensive test patterns]

## MCP Tools for Development

### Database Exploration

```bash
# List tables
mcp_backstageloca_list_tables()

# Describe schema
mcp_backstageloca_describe_table({ table_name: "tracks" })

# Query data
mcp_backstageloca_read_query({ query: "SELECT * FROM tracks LIMIT 10" })
```

### Documentation Lookup

```bash
# Backstage backend patterns
mcp_context7_query-docs({ libraryId: "/backstage/backstage", query: "backend plugin database" })

# Knex.js migrations
mcp_context7_query-docs({ libraryId: "/knex/knex", query: "migration patterns" })
```

[See references/mcp-integration.md for complete MCP usage patterns]

## Pre-Merge Checklist

- [ ] All tests pass: `yarn test --no-watch`
- [ ] TypeScript compiles: `yarn tsc --noEmit`
- [ ] Test coverage: 80% overall, 90% domain/application
- [ ] OpenAPI spec updated (all endpoints: 200, 400, 404, 500)
- [ ] Error handling per error mapping table
- [ ] Parameterized queries only (NO string concatenation)
- [ ] JSON/JSONB queries use safe extraction/casting (no string functions directly on JSONB)
- [ ] Schema/migrations validated against Azure PostgreSQL Flexible constraints
- [ ] Health checks registered
- [ ] techDocs/ updated (ARCHITECTURE.md, API.md, DATABASE.md)
- [ ] Architecture layers respected (Domain pure, Services use repositories only)
- [ ] Logging at boundaries (no secrets logged)
- [ ] Configuration externalized (no hardcoded credentials)

## Reference Files

| Topic                   | Reference File                                                         |
| ----------------------- | ---------------------------------------------------------------------- |
| **Architecture Layers** | [references/architecture-layers.md](references/architecture-layers.md) |
| **Database Patterns**   | [references/database-patterns.md](references/database-patterns.md)     |
| **Error Handling**      | [references/error-handling.md](references/error-handling.md)           |
| **Testing Strategy**    | [references/testing-strategy.md](references/testing-strategy.md)       |
| **Folder Structure**    | [references/folder-structure.md](references/folder-structure.md)       |
| **MCP Integration**     | [references/mcp-integration.md](references/mcp-integration.md)         |
| **Yarn Workflows**      | [references/yarn-workflows.md](references/yarn-workflows.md)           |

## Development Commands

```bash
# Build plugin
cd plugins/[plugin-name]-backend && yarn build

# Run tests
yarn test --no-watch

# TypeScript check
yarn tsc --noEmit

# Start backend
yarn start
```
