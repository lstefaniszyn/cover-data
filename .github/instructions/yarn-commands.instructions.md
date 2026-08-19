---
description: "Yarn commands and development workflows for this Backstage project. Use this as a quick reference for building, testing, and running the application."
applyTo: "**"
---

# Yarn Commands & Development Workflows

> Quick reference for all yarn commands, build processes, and common development workflows.

## 🚀 Root Level Commands

Run from `/workspaces/turbo-142964-backstage-playground`:

| Command                | Description                                                                  |
| ---------------------- | ---------------------------------------------------------------------------- |
| `yarn start`           | **Start Backstage in development mode** (frontend + backend with hot reload) |
| `yarn build:backend`   | Build backend only                                                           |
| `yarn build:all`       | Build all packages and plugins                                               |
| `yarn build-image`     | Build Docker image for backend (for deployment)                              |
| `yarn tsc`             | TypeScript compile                                                           |
| `yarn tsc --noEmit`    | **TypeScript check without emitting files** (use after code changes)         |
| `yarn tsc:full`        | Full TypeScript check without skipLibCheck (stricter, slower)                |
| `yarn test`            | Run tests (watch mode)                                                       |
| `yarn test --no-watch` | **Run tests without watch mode** (use before committing)                     |
| `yarn test:all`        | Run all tests with coverage                                                  |
| `yarn test:e2e`        | Run Playwright E2E tests                                                     |

> **See also**: `.github/instructions/test.frontend-e2e-playwright.instructions.md` for Playwright+Storybook E2E guidance, including Storybook webServer config, iframe selectors, and CI caching tips.
> | `yarn lint` | Lint changed files (since origin/master) |
> | `yarn lint:all` | Lint all files |
> | `yarn clean` | Clean build artifacts |
> | `yarn fix` | Auto-fix linting issues |
> | `yarn prettier:check` | Check formatting |
> | `yarn new` | Create new Backstage component |

## 📦 Plugin/Package Level Commands

Run from within a plugin or package directory:

| Command      | Description                  |
| ------------ | ---------------------------- |
| `yarn build` | Build the plugin/package     |
| `yarn start` | Start the plugin in dev mode |
| `yarn test`  | Test the plugin              |
| `yarn lint`  | Lint the plugin              |
| `yarn clean` | Clean build artifacts        |

## 🔧 Common Development Workflows

### Starting Development

```bash
# From project root
yarn start
```

This starts both frontend (port 3000) and backend (port 7007) with hot reload.

### After Making Code Changes

```bash
# Check TypeScript compiles
yarn tsc --noEmit

# Run tests
yarn test --no-watch
```

### Building a Specific Plugin

```bash
# Backend plugin
cd plugins/backstage-plugin-quality-check-backend-backend && yarn build

# Frontend plugin
cd plugins/backstage-plugin-quality-check && yarn build
```

### Full Build Before Commit

```bash
yarn tsc --noEmit && yarn test --no-watch && yarn lint
```

## 🗄️ Database Commands

### Access PostgreSQL

```bash
# Interactive psql session
docker exec -it turbo-142964-backstage-playground_devcontainer-db-1 psql -U postgres -d quality_check

# Run a single query
docker exec turbo-142964-backstage-playground_devcontainer-db-1 psql -U postgres -d quality_check -c "SELECT * FROM qualitycheck_fact;"
```

### Common Database Queries

```bash
# List all facts
docker exec turbo-142964-backstage-playground_devcontainer-db-1 psql -U postgres -d quality_check -c "SELECT entity_ref, fact_ref FROM qualitycheck_fact;"

# List all checks
docker exec turbo-142964-backstage-playground_devcontainer-db-1 psql -U postgres -d quality_check -c "SELECT id, name FROM checker LIMIT 10;"

# Check table structure
docker exec turbo-142964-backstage-playground_devcontainer-db-1 psql -U postgres -d quality_check -c "\d qualitycheck_fact"
```

## 🌐 API Endpoints (when running)

| Endpoint                                  | Method | Description                                  |
| ----------------------------------------- | ------ | -------------------------------------------- |
| `http://localhost:3000`                   | -      | Frontend UI                                  |
| `http://localhost:7007`                   | -      | Backend API                                  |
| `/api/quality-check/checks?entityRef=...` | GET    | Get checks for entity (with fact evaluation) |
| `/api/quality-check/qualitycheck/facts`   | POST   | Create/update facts                          |
| `/api/quality-check/tracks?entityRef=...` | GET    | Get tracks/certifications for entity         |

## 📁 Key Directories

| Path                                                      | Description                    |
| --------------------------------------------------------- | ------------------------------ |
| `packages/app/`                                           | Frontend Backstage app         |
| `packages/backend/`                                       | Backend Backstage app          |
| `plugins/backstage-plugin-quality-check/`                 | Quality Check frontend plugin  |
| `plugins/backstage-plugin-quality-check-backend-backend/` | Quality Check backend plugin   |
| `soundcheck/`                                             | Soundcheck YAML configurations |

## 🐳 Docker Commands

```bash
# List running containers
docker ps

# View container logs
docker logs turbo-142964-backstage-playground_devcontainer-db-1

# Restart database container
docker restart turbo-142964-backstage-playground_devcontainer-db-1
```

## ⚡ Quick Reference for AI Agents

When working on this project:

1. **After code changes:** `yarn tsc --noEmit`
2. **Before committing:** `yarn test --no-watch`
3. **To rebuild backend plugin:** `cd plugins/backstage-plugin-quality-check-backend-backend && yarn build`
4. **To rebuild frontend plugin:** `cd plugins/backstage-plugin-quality-check && yarn build`
5. **To start dev server:** `yarn start`
6. **Database access:** Use `docker exec ... psql` commands above

## ⚠️ Terminal Management Rules

**IMPORTANT:** Always use separate terminals for different tasks:

- **Terminal 1:** Reserved for `yarn start` (keep running, don't interrupt)
- **Terminal 2+:** Use for other commands (build, test, database queries, curl, etc.)

**NEVER:**

- Run commands in the same terminal where `yarn start` is running
- Interrupt `yarn start` with Ctrl+C to run other commands
- Mix long-running processes with one-off commands

**Example workflow:**

```bash
# Terminal 1 - Start and leave running
yarn start

# Terminal 2 - Run other commands
yarn tsc --noEmit
yarn test --no-watch
docker exec ... psql ...
curl http://localhost:7007/...
```
