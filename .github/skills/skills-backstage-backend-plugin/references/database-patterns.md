# Database Patterns

> Type-safe, parameterized database access for Backstage backend plugins.

## Core Pattern

Inject `coreServices.database` + `coreServices.rootHealth`; use Knex query builder with parameterized queries.

---

## Azure Database for PostgreSQL Flexible Server (Required Context)

- Target production assumptions to Azure Database for PostgreSQL Flexible Server behavior
- Treat semi-structured columns as explicit schema design, not ad-hoc blobs
- Keep business-critical predicates in typed columns; use JSON/JSONB for evolving attributes
- Prefer `jsonb` when filtering/searching semi-structured fields
- Plan indexes explicitly for JSON/JSONB query paths (for example GIN on frequently searched documents)

### JSON/JSONB Safety Rules

- Never call string functions directly on JSONB without extraction/casting
- For text search on full JSONB document: `column::text ILIKE ?`
- For key-level filtering, prefer extraction operators (`->>`, `#>>`) then compare
- Keep query bindings parameterized; avoid interpolated raw SQL

### Example: JSONB Filter Pitfall

```ts
// BAD: LOWER(jsonb) fails
query.whereRaw("LOWER(COALESCE(contacts, ?)) LIKE ?", ["", `%${poc.toLowerCase()}%`]);

// GOOD: cast JSONB to text first
query.whereRaw("contacts::text ILIKE ?", [`%${poc}%`]);
```

### Schema Guidance for Semi-Structured Data

- Define JSON/JSONB field ownership and shape in techDocs DATABASE.md
- Add defaults (`defaultTo('[]')` or `defaultTo('{}')`) for non-null JSON fields when appropriate
- Add CHECK constraints for enum-like scalar columns instead of only encoding status in JSON
- Document migration/backfill steps whenever moving between scalar and JSON/JSONB representations

---

## Database Layer Rules

| Rule                                                                          | Applies When                   |
| ----------------------------------------------------------------------------- | ------------------------------ |
| MUST inject via `coreServices.database`                                       | Accessing database             |
| MUST use Knex query builder with parameterized queries                        | Executing SQL                  |
| MUST register health checks via `coreServices.rootHealth`                     | Plugin initialization          |
| MUST keep migrations portable across PostgreSQL and SQLite                    | Writing/maintaining migrations |
| MAY extract plugin-specific config from `backend.database.plugin.<plugin-id>` | Custom DB settings needed      |

**Resources:**

- [DatabaseService](https://backstage.io/docs/backend-system/core-services/database)
- [RootHealth](https://backstage.io/docs/backend-system/core-services/root-health/)

---

## Setup Example

```ts
// plugin.ts
import { createBackendPlugin } from "@backstage/backend-plugin-api";

export const myPlugin = createBackendPlugin({
  pluginId: "my-plugin",
  register(env) {
    env.registerInit({
      deps: {
        database: coreServices.database,
        health: coreServices.rootHealth,
        logger: coreServices.logger,
        http: coreServices.httpRouter,
      },
      async init({ database, health, logger, http }) {
        // Get Knex instance
        const db = await database.getClient();

        // Register health check
        health.addReadinessCheck("database", async () => {
          try {
            await db.raw("SELECT 1");
            return { status: 200, message: "Database OK" };
          } catch (error) {
            return { status: 503, message: "Database unavailable" };
          }
        });

        // Create repository with db instance
        const repo = new TrackRepository(db, logger);
        const service = new TrackService(repo);
        const controller = new TrackController(service, logger);

        // Register routes
        http.use(createRouter({ controller }));
      },
    });
  },
});
```

---

## Repository Pattern

### Basic Repository

```ts
import type { Knex } from "knex";
import type { LoggerService } from "@backstage/backend-plugin-api";
import type { Track } from "../types/track.types";
import { NotFoundError, DatabaseError } from "../errors";

export class TrackRepository {
  constructor(
    private readonly db: Knex,
    private readonly logger: LoggerService,
  ) {}

  async findById(id: string): Promise<Track | null> {
    try {
      this.logger.info(`Fetching track ${id}`);

      const row = await this.db("tracks").where({ id }).first();

      if (!row) {
        return null;
      }

      return this.toDomain(row);
    } catch (error) {
      this.logger.error(`Failed to fetch track ${id}`, error);
      throw new DatabaseError("Failed to fetch track", error as Error);
    }
  }

  async create(track: Omit<Track, "id" | "createdAt">): Promise<Track> {
    try {
      const [inserted] = await this.db("tracks")
        .insert({
          name: track.name,
          description: track.description,
          created_at: new Date(),
        })
        .returning("*");

      return this.toDomain(inserted);
    } catch (error) {
      this.logger.error("Failed to create track", error);
      throw new DatabaseError("Failed to create track", error as Error);
    }
  }

  async update(id: string, updates: Partial<Track>): Promise<Track> {
    try {
      const [updated] = await this.db("tracks")
        .where({ id })
        .update({
          name: updates.name,
          description: updates.description,
          updated_at: new Date(),
        })
        .returning("*");

      if (!updated) {
        throw new NotFoundError("Track", id);
      }

      return this.toDomain(updated);
    } catch (error) {
      if (error instanceof NotFoundError) {
        throw error;
      }
      this.logger.error(`Failed to update track ${id}`, error);
      throw new DatabaseError("Failed to update track", error as Error);
    }
  }

  async delete(id: string): Promise<void> {
    try {
      const deleted = await this.db("tracks").where({ id }).delete();

      if (deleted === 0) {
        throw new NotFoundError("Track", id);
      }
    } catch (error) {
      if (error instanceof NotFoundError) {
        throw error;
      }
      this.logger.error(`Failed to delete track ${id}`, error);
      throw new DatabaseError("Failed to delete track", error as Error);
    }
  }

  private toDomain(row: any): Track {
    return {
      id: row.id,
      name: row.name,
      description: row.description,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }
}
```

---

## Parameterized Queries

### ✅ Good - Parameterized

```ts
// Using where clause
const tracks = await db("tracks").where({ userId: req.body.userId }).select("*");

// Using whereIn for multiple values
const tracks = await db("tracks").whereIn("id", trackIds).select("*");

// Using whereRaw with bindings
const tracks = await db("tracks").whereRaw("created_at > ?", [startDate]).select("*");
```

### ❌ Bad - String Concatenation (SQL Injection Risk)

```ts
// NEVER DO THIS
const tracks = await db.raw(`SELECT * FROM tracks WHERE user_id = '${userId}'`);

// NEVER DO THIS
const query = `SELECT * FROM tracks WHERE name = '${name}'`;
const tracks = await db.raw(query);
```

---

## Transactions

### Basic Transaction

```ts
async createTrackWithLevels(
  track: Omit<Track, 'id'>,
  levels: Level[],
): Promise<Track> {
  return this.db.transaction(async (trx) => {
    // Insert track
    const [insertedTrack] = await trx('tracks')
      .insert({
        name: track.name,
        description: track.description,
      })
      .returning('*');

    // Insert levels
    await trx('levels').insert(
      levels.map(level => ({
        track_id: insertedTrack.id,
        name: level.name,
        requirements: JSON.stringify(level.requirements),
      }))
    );

    // Return domain object
    return this.toDomain(insertedTrack);
  });
}
```

### Rollback on Error

```ts
async complexOperation(): Promise<void> {
  try {
    await this.db.transaction(async (trx) => {
      // Multiple operations
      await trx('tracks').insert({ /* ... */ });
      await trx('certifications').insert({ /* ... */ });

      // If any operation fails, transaction rolls back automatically
    });
  } catch (error) {
    this.logger.error('Transaction failed', error);
    throw new DatabaseError('Complex operation failed', error as Error);
  }
}
```

---

## Joins and Relations

### One-to-Many

```ts
async findWithLevels(trackId: string): Promise<Track & { levels: Level[] }> {
  const rows = await this.db('tracks')
    .leftJoin('levels', 'tracks.id', 'levels.track_id')
    .where('tracks.id', trackId)
    .select(
      'tracks.*',
      'levels.id as level_id',
      'levels.name as level_name',
      'levels.requirements as level_requirements',
    );

  if (rows.length === 0) {
    throw new NotFoundError('Track', trackId);
  }

  // Map to domain object
  const track = this.toDomain(rows[0]);
  const levels = rows
    .filter(row => row.level_id)
    .map(row => ({
      id: row.level_id,
      name: row.level_name,
      requirements: JSON.parse(row.level_requirements),
    }));

  return { ...track, levels };
}
```

---

## Pagination

```ts
interface PaginationOptions {
  page: number;
  limit: number;
}

interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}

async findAllPaginated(
  options: PaginationOptions,
): Promise<PaginatedResult<Track>> {
  const { page, limit } = options;
  const offset = (page - 1) * limit;

  // Get total count
  const [{ count }] = await this.db('tracks').count('* as count');

  // Get paginated results
  const rows = await this.db('tracks')
    .select('*')
    .limit(limit)
    .offset(offset)
    .orderBy('created_at', 'desc');

  return {
    items: rows.map(row => this.toDomain(row)),
    total: Number(count),
    page,
    limit,
    hasMore: offset + rows.length < Number(count),
  };
}
```

---

## Migrations

### Migration Portability (Required)

All plugin migrations MUST run on both PostgreSQL and SQLite.

#### ✅ Prefer

- `knex.schema.hasTable(...)` / `knex.schema.hasColumn(...)` guards for idempotency
- App-generated UUIDs (for example `randomUUID()`) instead of DB-specific UUID functions
- JSON stored via `table.json(...)` (or `text` + `JSON.stringify`) when portability is required
- Additive schema changes first; backfill in explicit query steps

#### ❌ Avoid

- PostgreSQL-only functions in migrations (`gen_random_uuid()`, `uuid_generate_v4()`, extensions)
- Alter-column flows that are unreliable on SQLite (`.alter()` for type/nullability/default changes)
- Dialect-specific raw SQL unless guarded by `knex.client.config.client`

#### Alter-Column Strategy

When nullability/type/default must change, prefer **create-copy-swap** over `.alter()`:

1. Create a new temp table with target schema
2. Copy/transforms rows into temp table
3. Drop old table
4. Rename temp table to original name

This avoids SQLite alter-table limitations and keeps migrations deterministic.

### Migration Files

Place migrations in `migrations/` directory:

```
plugins/my-plugin-backend/
├── migrations/
│   ├── 20240101000000_create_tracks.js
│   └── 20240102000000_add_levels.js
```

### Example Migration

```js
// migrations/20240101000000_create_tracks.js

exports.up = async function (knex) {
  await knex.schema.createTable("tracks", (table) => {
    table.increments("id").primary();
    table.string("name").notNullable();
    table.text("description");
    table.boolean("draft").defaultTo(true);
    table.timestamps(true, true);
  });
};

exports.down = async function (knex) {
  await knex.schema.dropTable("tracks");
};
```

### Portable Migration Example (SQLite + PostgreSQL)

```ts
import type { Knex } from "knex";
import { randomUUID } from "node:crypto";

export async function up(knex: Knex): Promise<void> {
  const hasConfig = await knex.schema.hasTable("plugin_config");
  if (!hasConfig) {
    await knex.schema.createTable("plugin_config", (table) => {
      table.uuid("id").primary();
      table.boolean("enabled").notNullable().defaultTo(true);
      table.text("settings_json").notNullable().defaultTo("[]");
      table.timestamp("created_at", { useTz: true }).defaultTo(knex.fn.now());
    });
  }

  const existing = await knex("plugin_config").first("id");
  if (!existing) {
    await knex("plugin_config").insert({
      id: randomUUID(),
      enabled: true,
      settings_json: JSON.stringify([]),
    });
  }
}

export async function down(knex: Knex): Promise<void> {
  await knex.schema.dropTableIfExists("plugin_config");
}
```

### Run Migrations

```bash
# Apply migrations
yarn workspace @internal/plugin-my-plugin-backend migrate:latest

# Rollback last migration
yarn workspace @internal/plugin-my-plugin-backend migrate:down
```

---

## Health Checks

### Database Health Check

```ts
health.addReadinessCheck("database", async () => {
  try {
    await db.raw("SELECT 1");
    return { status: 200, message: "Database connection OK" };
  } catch (error) {
    logger.error("Database health check failed", error);
    return {
      status: 503,
      message: "Database connection failed",
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
});
```

---

## Configuration

### Extract Database Config

```ts
// Get plugin-specific database config
const config = env.config;
const dbConfig = config.getOptionalConfig("backend.database.plugin.my-plugin");

if (dbConfig) {
  const connectionString = dbConfig.getString("connection.connectionString");
  const poolMin = dbConfig.getOptionalNumber("connection.pool.min") || 2;
  const poolMax = dbConfig.getOptionalNumber("connection.pool.max") || 10;

  logger.info(`Using custom DB config: pool ${poolMin}-${poolMax}`);
}
```

### Example app-config.yaml

```yaml
backend:
  database:
    client: pg
    connection:
      host: localhost
      port: 5432
      user: postgres
      password: postgres
      database: backstage
    plugin:
      my-plugin:
        connection:
          connectionString: postgresql://user:pass@host:5432/customdb
          pool:
            min: 2
            max: 10
```

---

## Pre-Merge Checklist

- [ ] All queries use parameterized bindings
- [ ] No string concatenation in SQL
- [ ] JSON/JSONB queries use extraction/casting before text functions
- [ ] Transactions used for multi-step operations
- [ ] Error handling wraps DB errors in domain errors
- [ ] Health check registered for database
- [ ] Migrations tested (up and down)
- [ ] Migrations verified on SQLite and PostgreSQL
- [ ] Azure PostgreSQL Flexible compatibility considered for schema/index strategy
- [ ] No PostgreSQL-only functions/extensions used in migrations
- [ ] No unguarded `.alter()` in migrations
- [ ] Logging at repository boundaries
- [ ] Repository returns domain objects (not raw rows)
