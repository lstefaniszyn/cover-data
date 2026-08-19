# Database & Schema Evolution Patterns

> Manage database changes incrementally with zero-downtime migrations and rollback safety.

## Core Principle

**Database changes are versioned, tested, and rolled out incrementally** alongside application code. All migrations must be **backwards-compatible** and **reversible**.

---

## Migration Strategies

### Expand-Contract Pattern

**Pattern:** Make schema changes in three phases to allow zero-downtime deployments.

**Phases:**

1. **Expand** — Add new schema elements (columns, tables) without removing old ones
2. **Migrate** — Run application code that writes to both old and new schema
3. **Contract** — Remove old schema elements after migration is complete

**Example (Renaming a column):**

```typescript
// Phase 1: Expand - Add new column
exports.up = async function (knex) {
  await knex.schema.alterTable("events", (table) => {
    table.string("location_name").nullable(); // New column
  });
};

// Phase 2: Migrate - Application writes to both columns
export class EventRepository {
  async createEvent(event: Event): Promise<Event> {
    await this.db("events").insert({
      location: event.location, // Old column
      location_name: event.location, // New column (same value)
      // ...
    });
  }
}

// Phase 3: Contract - Remove old column (separate migration)
exports.up = async function (knex) {
  await knex.schema.alterTable("events", (table) => {
    table.dropColumn("location"); // Old column removed
  });
};
```

---

## Migration Best Practices

**Rules:**

- Every migration has an **up** and **down** script
- Migrations are **idempotent** (can run multiple times safely)
- Test migrations in a **production-like copy** before deploying
- Migrations run **before application deployment** (not during startup)
- Capture schema and data before large migrations (backups)
- Use transactions for **atomic** migrations (all-or-nothing)

**Anti-Patterns:**

- Breaking changes that require downtime
- Migrations that run during application startup
- Non-reversible migrations
- Large data migrations that lock tables for minutes

---

## Knex Migration Template

```typescript
import type { Knex } from "knex";

export async function up(knex: Knex): Promise<void> {
  // Use transaction for atomic changes
  await knex.transaction(async (trx) => {
    // Add new table
    await trx.schema.createTable("mentor_profiles", (table) => {
      table.increments("id").primary();
      table.string("user_ref").notNullable().unique();
      table.text("bio");
      table.jsonb("skills").defaultTo("[]");
      table.timestamps(true, true); // created_at, updated_at
    });

    // Add index for common queries
    await trx.schema.alterTable("mentor_profiles", (table) => {
      table.index("user_ref");
    });
  });
}

export async function down(knex: Knex): Promise<void> {
  await knex.schema.dropTableIfExists("mentor_profiles");
}
```

---

## Zero-Downtime Migration Checklist

**For additive changes (safe):**

- [ ] Add new columns as nullable
- [ ] Add new tables
- [ ] Add indexes (non-blocking if possible)
- [ ] Add new constraints

**For destructive changes (requires expand-contract):**

- [ ] Phase 1: Add new schema elements
- [ ] Deploy application version that writes to both old and new
- [ ] Phase 2: Backfill data (if needed)
- [ ] Verify data consistency
- [ ] Deploy application version that reads from new schema only
- [ ] Phase 3: Remove old schema elements

---

## Data Backfilling

**Pattern:** Populate new columns or tables with data from existing records.

**Example:**

```typescript
export async function up(knex: Knex): Promise<void> {
  // Phase 1: Add new column
  await knex.schema.alterTable("events", (table) => {
    table.integer("attendee_count").defaultTo(0);
  });

  // Phase 2: Backfill data in batches
  const BATCH_SIZE = 1000;
  let offset = 0;
  let hasMore = true;

  while (hasMore) {
    const events = await knex("events").select("id").limit(BATCH_SIZE).offset(offset);

    if (events.length === 0) {
      hasMore = false;
      break;
    }

    // Update each event with calculated attendee count
    for (const event of events) {
      const count = await knex("event_registrations").where("event_id", event.id).count("* as count");

      await knex("events").where("id", event.id).update({ attendee_count: count[0].count });
    }

    offset += BATCH_SIZE;
  }
}
```

---

## Migration Testing

**Before Production:**

1. **Test on production-like copy** with real data volumes
2. **Measure migration duration** (should complete in seconds/minutes, not hours)
3. **Verify rollback** works correctly
4. **Test application** against both old and new schema
5. **Run performance tests** after migration

**Example Test:**

```typescript
describe("Migration: Add location_name column", () => {
  let db: Knex;

  beforeEach(async () => {
    db = await createTestDatabase();
    await db.migrate.up(); // Run migration
  });

  afterEach(async () => {
    await db.migrate.down(); // Rollback
    await db.destroy();
  });

  it("should add location_name column as nullable", async () => {
    const columns = await db("events").columnInfo();
    expect(columns.location_name).toBeDefined();
    expect(columns.location_name.nullable).toBe(true);
  });

  it("should allow inserting events without location_name", async () => {
    await expect(db("events").insert({ title: "Test Event", location: "Room A" })).resolves.not.toThrow();
  });
});
```

---

## Schema Evolution Decision Tree

```
Need to change database schema?
├─ Adding new table/column? → Safe, deploy directly
├─ Renaming column/table? → Use Expand-Contract (3 phases)
├─ Removing column/table? → Use Expand-Contract (3 phases)
├─ Changing column type? → Use Expand-Contract + backfill
├─ Large data migration? → Run as separate batch job (not during deployment)
└─ Multiple schema changes? → Break into multiple migrations (one change per migration)
```

---

## Pre-Merge Checklist

- [ ] Migration has both `up` and `down` scripts
- [ ] Migration is idempotent (can run multiple times)
- [ ] Breaking changes use Expand-Contract pattern
- [ ] Migrations tested on production-like copy
- [ ] Backfill data in batches (if needed)
- [ ] Migration duration measured (<1 min target)
- [ ] Rollback tested and verified
- [ ] Application code compatible with both old and new schema (during transition)
- [ ] Database backup taken before production deployment

---

**Golden Rule:** If a migration causes downtime or data loss, it's **not ready** for production.
