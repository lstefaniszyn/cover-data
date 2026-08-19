# Security & Compliance Patterns (Shift-Left)

> Integrate security into every stage of development, not just at the end.

## Core Principle

**Shift security left**: Find and fix vulnerabilities early in the development cycle, not after deployment.

---

## Security in the Pipeline

**Pattern:** Automate security checks at every stage of the delivery pipeline.

**Pipeline Stages:**

1. **Pre-Commit** — IDE plugins, git hooks (secret scanning)
2. **Commit** — Static analysis (SAST), dependency scanning
3. **Build** — Container scanning, license checks
4. **Deploy** — Dynamic analysis (DAST), penetration testing
5. **Production** — Runtime monitoring, anomaly detection

---

## Dependency Scanning

**Pattern:** Scan dependencies for known vulnerabilities (CVEs) on every build.

**Tools:**

- `npm audit` / `yarn audit` (Node.js)
- Snyk, WhiteSource, GitHub Dependabot
- OWASP Dependency-Check

**Example CI Check:**

```yaml
# .github/workflows/security.yml
name: Security Scan
on: [push, pull_request]
jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run npm audit
        run: npm audit --audit-level=high
      - name: Snyk scan
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
```

**Remediation:**

- **High/Critical CVEs**: Fix immediately (patch or replace dependency)
- **Medium CVEs**: Fix within 30 days
- **Low CVEs**: Fix opportunistically

---

## Secret Management

**Pattern:** Never commit secrets; inject at runtime via secure vaults.

**Rules:**

- Use **environment variables** or **secret management services** (Azure Key Vault, AWS Secrets Manager)
- Rotate secrets regularly (every 90 days)
- Use **short-lived tokens** where possible
- Scan commits for secrets before they reach remote

**Example Secret Scanning (Pre-Commit Hook):**

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Scan for secrets using truffleHog
trufflehog filesystem . --fail --json > /dev/null
if [ $? -ne 0 ]; then
  echo "❌ Secret detected! Commit blocked."
  exit 1
fi

echo "✅ No secrets detected"
exit 0
```

**Example Secret Injection:**

```typescript
// ❌ BAD: Hardcoded secret
const apiKey = "sk-1234567890abcdef";

// ✅ GOOD: Injected from environment
const apiKey = process.env.API_KEY;
if (!apiKey) {
  throw new Error("API_KEY environment variable not set");
}
```

---

## Static Application Security Testing (SAST)

**Pattern:** Analyze code for security vulnerabilities before runtime.

**Tools:**

- ESLint with security plugins (`eslint-plugin-security`)
- SonarQube, Checkmarx, Fortify
- Semgrep (pattern-based scanning)

**Example ESLint Security Rules:**

```json
{
  "extends": ["plugin:security/recommended"],
  "rules": {
    "security/detect-object-injection": "error",
    "security/detect-non-literal-regexp": "warn",
    "security/detect-unsafe-regex": "error",
    "security/detect-sql-injection": "error"
  }
}
```

---

## Input Validation & Sanitization

**Pattern:** **Never trust user input**. Validate, sanitize, and encode all external data.

**Rules:**

- Validate input **structure** (schema validation with Zod, Joi)
- Sanitize input **content** (remove/escape dangerous characters)
- Use **parameterized queries** for databases (prevent SQL injection)
- Use **CSP headers** to prevent XSS
- Use **rate limiting** to prevent abuse

**Example Schema Validation:**

```typescript
import { z } from "zod";

const createEventSchema = z.object({
  title: z.string().min(1).max(200),
  description: z.string().max(5000),
  startDate: z.string().datetime(),
  location: z.string().min(1).max(100),
});

export function validateCreateEventInput(input: unknown) {
  return createEventSchema.parse(input); // Throws if invalid
}
```

**Example Parameterized Query:**

```typescript
// ❌ BAD: SQL injection vulnerability
const query = `SELECT * FROM events WHERE id = ${req.params.id}`;

// ✅ GOOD: Parameterized query
const query = db("events").where("id", req.params.id);
```

---

## Authentication & Authorization

**Pattern:** **Authenticate** who the user is; **authorize** what they can do.

**Rules:**

- Use **strong authentication** (OAuth2, OIDC, SAML)
- Enforce **MFA** for privileged accounts
- Use **short-lived tokens** (JWTs with expiration)
- Implement **RBAC** (Role-Based Access Control) or **ABAC** (Attribute-Based)
- Log all authentication and authorization events

**Example Authorization Middleware:**

```typescript
import { Request, Response, NextFunction } from "express";

export function requireRole(role: string) {
  return (req: Request, res: Response, next: NextFunction) => {
    const user = req.user; // Populated by authentication middleware

    if (!user) {
      return res.status(401).json({ error: "Unauthorized" });
    }

    if (!user.roles.includes(role)) {
      return res.status(403).json({ error: "Forbidden" });
    }

    next();
  };
}

// Usage
app.post("/api/events", requireRole("event:admin"), createEventHandler);
```

---

## Container Security

**Pattern:** Scan container images for vulnerabilities before deploying.

**Rules:**

- Use **minimal base images** (alpine, distroless)
- Scan images with Trivy, Clair, Snyk Container
- Run containers as **non-root** user
- Use **image signing** to verify provenance
- Regularly update base images (rebuild weekly)

**Example Dockerfile:**

```dockerfile
# Use minimal base image
FROM node:20-alpine

# Create non-root user
RUN addgroup -S backstage && adduser -S backstage -G backstage

# Set working directory
WORKDIR /app

# Copy dependencies
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile --production

# Copy application code
COPY --chown=backstage:backstage . .

# Switch to non-root user
USER backstage

# Expose port
EXPOSE 7007

# Start application
CMD ["node", "dist/index.js"]
```

---

## HTTPS & TLS

**Pattern:** Enforce HTTPS for all traffic; use modern TLS versions.

**Rules:**

- Use **TLS 1.3** (or TLS 1.2 minimum)
- Use **strong ciphers** (disable weak ciphers)
- Enforce **HSTS** (HTTP Strict Transport Security)
- Use **valid certificates** (Let's Encrypt, commercial CA)
- Redirect HTTP → HTTPS automatically

**Example HSTS Header:**

```typescript
import { Request, Response, NextFunction } from "express";

export function hstsMiddleware(req: Request, res: Response, next: NextFunction) {
  res.setHeader("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload");
  next();
}
```

---

## Security Headers

**Pattern:** Set security headers to protect against common attacks.

**Required Headers:**

```typescript
import helmet from "helmet";
import express from "express";

const app = express();

// Use Helmet to set security headers
app.use(
  helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'", "'unsafe-inline'"], // Avoid unsafe-inline in production
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", "data:", "https:"],
      },
    },
    hsts: {
      maxAge: 31536000,
      includeSubDomains: true,
      preload: true,
    },
    frameguard: { action: "deny" }, // Prevent clickjacking
    noSniff: true, // Prevent MIME sniffing
    xssFilter: true, // Enable XSS filter
  }),
);
```

---

## Rate Limiting & DDoS Protection

**Pattern:** Limit request rates to prevent abuse and DDoS attacks.

**Example Rate Limiting:**

```typescript
import rateLimit from "express-rate-limit";

// Global rate limit
const globalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000, // Max 1000 requests per 15 minutes per IP
  message: "Too many requests, please try again later",
});

// Endpoint-specific rate limit (stricter)
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 10, // Max 10 login attempts per 15 minutes
  message: "Too many login attempts, please try again later",
});

app.use(globalLimiter);
app.post("/api/auth/login", authLimiter, loginHandler);
```

---

## Logging & Auditing

**Pattern:** Log all security-relevant events for audit and forensics.

**Events to Log:**

- Authentication attempts (success and failure)
- Authorization failures (403 Forbidden)
- Privilege escalations
- Data access (PII, sensitive data)
- Configuration changes
- Security alerts (suspicious activity)

**Example Audit Log:**

```typescript
import { Logger } from "@backstage/backend-plugin-api";

export class AuditLogger {
  constructor(private readonly logger: Logger) {}

  logAuthSuccess(userId: string, ip: string) {
    this.logger.info("Authentication successful", {
      event: "auth.success",
      userId,
      ip,
      timestamp: new Date().toISOString(),
    });
  }

  logAuthFailure(username: string, ip: string, reason: string) {
    this.logger.warn("Authentication failed", {
      event: "auth.failure",
      username,
      ip,
      reason,
      timestamp: new Date().toISOString(),
    });
  }

  logDataAccess(userId: string, resource: string, action: string) {
    this.logger.info("Data access", {
      event: "data.access",
      userId,
      resource,
      action,
      timestamp: new Date().toISOString(),
    });
  }
}
```

---

## Security Checklist (Shift-Left)

**Pre-Commit:**

- [ ] Secret scanning (truffleHog, git-secrets)
- [ ] IDE security plugins warn about vulnerabilities

**Commit Stage (CI):**

- [ ] Dependency scanning (npm audit, Snyk)
- [ ] SAST (ESLint security rules, Semgrep)
- [ ] License compliance check

**Build Stage:**

- [ ] Container image scanning (Trivy)
- [ ] Image built as non-root user
- [ ] Image signing for provenance

**Deploy Stage:**

- [ ] DAST (dynamic analysis)
- [ ] Infrastructure security scan (Kubernetes misconfigurations)

**Production:**

- [ ] Runtime monitoring (anomaly detection)
- [ ] Security headers configured (Helmet)
- [ ] Rate limiting in place
- [ ] Audit logging for security events
- [ ] HTTPS enforced with HSTS

---

## Pre-Merge Checklist

- [ ] All dependencies scanned (no high/critical CVEs)
- [ ] No secrets committed to Git
- [ ] Input validation with schema (Zod, Joi)
- [ ] Parameterized queries (no SQL injection)
- [ ] Authorization checks in place
- [ ] Security headers configured (Helmet)
- [ ] Rate limiting configured
- [ ] HTTPS enforced with HSTS
- [ ] Container runs as non-root user
- [ ] Audit logging for sensitive actions

---

**Golden Rule:** Security is **everyone's responsibility**, not just the security team's.
