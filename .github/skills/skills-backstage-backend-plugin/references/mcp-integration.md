# MCP Tools for Development

> AI agents SHOULD use these MCP servers to fetch up-to-date documentation and interact with databases during development.

## Available MCP Servers

This workspace has configured MCP servers that provide real-time access to documentation and databases. AI agents MUST prefer these over cached/training data when working on this project.

### 1. Context7 (Documentation Lookup)

**Server**: `context7` (via `mcp_context7_*` tools)
**Purpose**: Fetch up-to-date documentation for any programming library

**Available Tools**:
| Tool | Description |
|------|-------------|
| `mcp_context7_resolve-library-id` | Find the Context7 library ID for a package name |
| `mcp_context7_query-docs` | Query documentation for a specific library |

**Usage Pattern**:

1. First call `resolve-library-id` to get the exact library ID
2. Then call `query-docs` with the resolved ID

**Key Libraries for This Project**:
| Library | Context7 ID | Use For |
|---------|-------------|---------|
| Backstage | `/backstage/backstage` | Plugin development, APIs, configuration |
| React | `/facebook/react` | Hooks, components, patterns |
| Material UI | `/mui/material-ui` | MUI v5 components (also use mui-mcp below) |
| Knex.js | `/knex/knex` | Database queries, migrations |
| Express | `/expressjs/express` | HTTP routing, middleware |
| Zod | `/colinhacks/zod` | Schema validation |
| Jest | `/jestjs/jest` | Testing patterns |
| Playwright | `/microsoft/playwright` | E2E testing |

**Example**:

```
# Step 1: Resolve library ID
mcp_context7_resolve-library-id({ libraryName: "backstage", query: "how to create a backend plugin" })

# Step 2: Query documentation
mcp_context7_query-docs({ libraryId: "/backstage/backstage", query: "backend plugin authentication" })
```

**When to Use**:

- ✅ Uncertain about library API or recent changes
- ✅ Need code examples for specific features
- ✅ Checking best practices for a library
- ✅ Verifying configuration options

---

### 2. MUI MCP (Material UI Documentation)

**Server**: `mui-mcp` (via `mcp_mui-mcp_*` tools)
**Purpose**: Specialized access to Material UI documentation across versions

**Available Tools**:
| Tool | Description |
|------|-------------|
| `mcp_mui-mcp_useMuiDocs` | Get documentation index for MUI packages |
| `mcp_mui-mcp_fetchDocs` | Fetch specific documentation pages |

**Supported Packages**:

- `@mui/material` (v5.17.1, v6.4.12, v7.2.0)
- `@mui/x-charts`, `@mui/x-data-grid`, `@mui/x-date-pickers`, `@mui/x-tree-view`

**Usage Pattern**:

1. Call `useMuiDocs` with the llms.txt URL for the package version
2. Analyze the returned documentation structure
3. Call `fetchDocs` for specific component documentation

**Example**:

```
# Step 1: Get docs index for MUI v5
mcp_mui-mcp_useMuiDocs({ urlList: ["https://llms.mui.com/material-ui/5.17.1/llms.txt"] })

# Step 2: Fetch specific component docs
mcp_mui-mcp_fetchDocs({ urls: ["https://mui.com/material-ui/react-button/"] })
```

**When to Use**:

- ✅ Implementing MUI components (Button, Table, Dialog, etc.)
- ✅ Checking MUI v5 API and props
- ✅ Styling MUI components with `sx` prop
- ✅ Using MUI X components (DataGrid, DatePicker, Charts)

---

### 3. PostgreSQL MCP (Database Operations)

**Server**: `backstageLocalDB`, `qualityCheckDB`, etc. (via `mcp_backstageloca_*` tools)
**Purpose**: Query and manage PostgreSQL databases directly

**Available Tools**:
| Tool | Description |
|------|-------------|
| `mcp_backstageloca_list_tables` | List all tables in the database |
| `mcp_backstageloca_describe_table` | Get schema for a specific table |
| `mcp_backstageloca_read_query` | Execute SELECT queries |
| `mcp_backstageloca_write_query` | Execute INSERT, UPDATE, DELETE |
| `mcp_backstageloca_create_table` | Create new tables |
| `mcp_backstageloca_alter_table` | Modify table schema |
| `mcp_backstageloca_drop_table` | Remove tables (with confirmation) |
| `mcp_backstageloca_export_query` | Export query results to CSV/JSON |
| `mcp_backstageloca_append_insight` | Add business insight to memo |
| `mcp_backstageloca_list_insights` | List all business insights |

**Configured Databases**:
| Server Name | Database | Purpose |
|-------------|----------|---------|
| `backstageLocalDB` | `backstage` | Main Backstage database |
| `backstageLocalDBSoundcheck` | `soundcheck` | Soundcheck plugin data |
| `backstageLocalDBQualitycheck` | `quality_check` | Quality check plugin data |
| `qualityCheckDB` | `quality_check` | Quality check (alternate) |

**Example**:

```
# List tables
mcp_backstageloca_list_tables()

# Describe a table
mcp_backstageloca_describe_table({ table_name: "qualitycheck_fact" })

# Query data
mcp_backstageloca_read_query({ query: "SELECT * FROM qualitycheck_fact LIMIT 10" })

# Insert data
mcp_backstageloca_write_query({ query: "INSERT INTO ... VALUES ..." })
```

**When to Use**:

- ✅ Exploring existing database schema
- ✅ Verifying data after migrations
- ✅ Debugging backend data issues
- ✅ Testing queries before implementing in code
- ✅ Creating/modifying test data

**Security Notes**:

- Always use parameterized queries in application code
- MCP tools are for development/debugging only
- Never expose MCP credentials in code

---

## Best Practices for AI Agents

### Documentation Lookup Priority

1. **First**: Use MCP tools (`context7`, `mui-mcp`) for library documentation
2. **Second**: Check repo instruction files (`.github/instructions/`)
3. **Last**: Use training data (may be outdated)

### When to Use Each MCP

| Task                         | Preferred MCP                          |
| ---------------------------- | -------------------------------------- |
| Backstage plugin development | `context7` with `/backstage/backstage` |
| MUI component implementation | `mui-mcp`                              |
| Database schema exploration  | `mcp_backstageloca_*`                  |
| General library docs         | `context7`                             |
| Testing patterns             | `context7` with relevant library       |

### Rate Limiting

- Do not call Context7 tools more than 3 times per question
- If information not found after 3 calls, use best available data
- Prefer specific queries over broad searches

### Example Workflow (Frontend Feature)

```
1. Check constitution.md for UI library priority (MUI v5 first)
2. Use mcp_mui-mcp_useMuiDocs to get component API
3. If complex Backstage integration, use mcp_context7_query-docs for Backstage patterns
4. Implement following frontend-architecture.instructions.md
```

### Example Workflow (Backend Feature)

```
1. Use mcp_backstageloca_describe_table to understand existing schema
2. Use mcp_context7_query-docs for Knex.js migration patterns
3. Use mcp_context7_query-docs for Backstage backend plugin patterns
4. Implement following backend-architecture.instructions.md
```
