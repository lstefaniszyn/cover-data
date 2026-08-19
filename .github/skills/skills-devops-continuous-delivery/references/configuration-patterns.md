# Configuration Patterns & Environment Management

> Externalize, version, and secure all configuration; maintain environment parity.

## Core Principle

**One Build, Many Environments**: The same immutable artifact is deployed to all environments with **external configuration**.

---

## Configuration Management

**Pattern:** All configuration is **versioned**, **externalized**, and **substituted at runtime** with environment-specific values.

**Rules:**

- Never hardcode environment-specific values (URLs, credentials, feature flags)
- Store configuration in version control (environment templates, schemas)
- Inject secrets via **secure vaults** (Azure Key Vault, AWS Secrets Manager, HashiCorp Vault)
- Never commit secrets to Git
- Use **config schemas** to validate configuration at startup

**Example Configuration Layers:**

```typescript
// app-config.yaml (default)
backend:
  baseUrl: http://localhost:7007
  database:
    client: pg

// app-config.production.yaml (override)
backend:
  baseUrl: https://api.example.com
  database:
    connection:
      host: ${POSTGRES_HOST}
      user: ${POSTGRES_USER}
      password: ${POSTGRES_PASSWORD_SECRET}
```

---

## Environment Parity

**Pattern:** Keep environments as **similar as possible** to reduce surprises.

**Rules:**

- Use the **same OS, runtime versions, libraries** across environments
- Use **infrastructure as code** to provision environments (Terraform, Kubernetes manifests)
- Automate environment creation; **avoid** manual configuration
- Run **smoke tests** after deployment to verify environment health
- Log **environment metadata** (cluster, region, version) with every request

**Anti-Patterns:**

- "Works on my machine" discrepancies
- Manual environment setup
- Different versions of dependencies in dev vs. production

**Example Environment Metadata:**

```typescript
import { MiddlewareFactory } from "@backstage/backend-plugins-api";

export const createEnvironmentMiddleware = (): MiddlewareFactory => {
  return {
    middleware: (req, res, next) => {
      req.context = {
        environment: process.env.ENVIRONMENT_NAME || "local",
        region: process.env.AWS_REGION || "unknown",
        version: process.env.APP_VERSION || "dev",
      };
      next();
    },
  };
};
```

---

## Configuration Validation

**Pattern:** Validate configuration at **application startup** to fail fast.

**Example:**

```typescript
import { z } from "zod";

const configSchema = z.object({
  backend: z.object({
    baseUrl: z.string().url(),
    database: z.object({
      client: z.enum(["pg", "sqlite3"]),
      connection: z.object({
        host: z.string(),
        port: z.number().int().default(5432),
        user: z.string(),
        password: z.string(),
      }),
    }),
  }),
});

export function validateConfig(config: unknown) {
  try {
    return configSchema.parse(config);
  } catch (error) {
    throw new Error(`Invalid configuration: ${error.message}`);
  }
}
```

---

## Secret Management

**Rules:**

- **Never** commit secrets to version control
- Use **secret management services** (Azure Key Vault, AWS Secrets Manager)
- Rotate secrets regularly
- Inject secrets at runtime via environment variables or mount points
- Audit secret access

**Example Secret Injection (Kubernetes):**

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: backstage-backend
spec:
  containers:
    - name: backend
      image: backstage-backend:latest
      env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-credentials
              key: password
```

---

## Feature Flags

**Pattern:** Control feature rollout and rollback **without redeploying**.

**Rules:**

- Use feature flags for incomplete or risky features
- Decouple **deployment** from **release**
- Remove flags after full rollout (avoid flag debt)
- Use a feature flag service (LaunchDarkly, Unleash, or custom)

**Example:**

```typescript
import { FeatureFlagService } from "./feature-flags";

export class EventService {
  constructor(private readonly flags: FeatureFlagService) {}

  async createEvent(event: Event): Promise<Event> {
    if (this.flags.isEnabled("event.promotion")) {
      return this.createPromotedEvent(event);
    }
    return this.createStandardEvent(event);
  }
}
```

---

## Environment-Specific Configuration Matrix

| Configuration | Dev                | Staging                      | Production                             |
| ------------- | ------------------ | ---------------------------- | -------------------------------------- |
| **Database**  | SQLite             | PostgreSQL (single instance) | PostgreSQL (cluster, replicas)         |
| **Cache**     | In-memory          | Redis (single instance)      | Redis (cluster)                        |
| **Logging**   | Console            | Structured JSON → CloudWatch | Structured JSON → CloudWatch + Archive |
| **Metrics**   | Local (Prometheus) | CloudWatch                   | CloudWatch + Datadog                   |
| **Secrets**   | `.env` file        | Azure Key Vault              | Azure Key Vault                        |
| **TLS**       | None               | Self-signed                  | Valid certificates (Let's Encrypt)     |
| **Scaling**   | Single pod         | 2 replicas                   | 5+ replicas with autoscaling           |

---

## Pre-Merge Checklist

- [ ] Configuration is externalized (no hardcoded values)
- [ ] Secrets are injected via secure vaults
- [ ] Configuration schema is defined and validated at startup
- [ ] Same artifact runs in all environments
- [ ] Infrastructure as code (Terraform/Helm) provisions environments
- [ ] Feature flags control incomplete/risky features
- [ ] Environment metadata is logged with every request
- [ ] No secrets committed to Git

---

**Golden Rule:** If a configuration value changes between environments, it must be **external, versioned, and validated**.
