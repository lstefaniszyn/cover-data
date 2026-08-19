# Error Handling

> Define domain error hierarchy for type-safe error handling and HTTP mapping.

## Pattern

Extend `Error` with context; catch at boundaries, wrap, map to HTTP in controllers.

---

## Error Handling Rules

| Rule                                    | Applies When                  |
| --------------------------------------- | ----------------------------- |
| MUST extend `Error` with context fields | Creating domain error         |
| MUST catch at infrastructure boundaries | Gateway/repository operations |
| MUST wrap in domain error types         | External error occurs         |
| MUST map to HTTP status in controllers  | Returning error response      |

---

## Error Types & HTTP Mapping

| Error Type          | Context                  | Throw When                       | HTTP Code |
| ------------------- | ------------------------ | -------------------------------- | --------- |
| `ValidationError`   | field, value             | Input validation fails           | 400       |
| `UnauthorizedError` | (auth context)           | Authentication missing/invalid   | 401       |
| `ForbiddenError`    | (resource ref)           | Authorization check fails        | 403       |
| `NotFoundError`     | resourceType, resourceId | Resource not found in DB/API     | 404       |
| `ConflictError`     | reason, conflictingId    | State conflict (duplicate, etc.) | 409       |
| `DatabaseError`     | cause (wrapped Error)    | DB operation fails               | 500       |
| `GatewayError`      | cause (wrapped Error)    | External API call fails          | 502/503   |

---

## Error Class Definitions

### ValidationError

```ts
// errors/ValidationError.ts
export class ValidationError extends Error {
  readonly name = "ValidationError";

  constructor(
    public readonly field: string,
    public readonly value: unknown,
    message?: string,
  ) {
    super(message || `Validation failed for field "${field}"`);
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}
```

### NotFoundError

```ts
// errors/NotFoundError.ts
export class NotFoundError extends Error {
  readonly name = "NotFoundError";

  constructor(
    public readonly resourceType: string,
    public readonly resourceId: string,
  ) {
    super(`${resourceType} with id "${resourceId}" not found`);
    Object.setPrototypeOf(this, NotFoundError.prototype);
  }
}
```

### UnauthorizedError

```ts
// errors/UnauthorizedError.ts
export class UnauthorizedError extends Error {
  readonly name = "UnauthorizedError";

  constructor(message = "Authentication required") {
    super(message);
    Object.setPrototypeOf(this, UnauthorizedError.prototype);
  }
}
```

### ForbiddenError

```ts
// errors/ForbiddenError.ts
export class ForbiddenError extends Error {
  readonly name = "ForbiddenError";

  constructor(
    public readonly resource: string,
    message?: string,
  ) {
    super(message || `Access to ${resource} is forbidden`);
    Object.setPrototypeOf(this, ForbiddenError.prototype);
  }
}
```

### ConflictError

```ts
// errors/ConflictError.ts
export class ConflictError extends Error {
  readonly name = "ConflictError";

  constructor(
    public readonly reason: string,
    public readonly conflictingId?: string,
  ) {
    super(`Conflict: ${reason}${conflictingId ? ` (${conflictingId})` : ""}`);
    Object.setPrototypeOf(this, ConflictError.prototype);
  }
}
```

### DatabaseError

```ts
// errors/DatabaseError.ts
export class DatabaseError extends Error {
  readonly name = "DatabaseError";

  constructor(
    message: string,
    public readonly cause: Error,
  ) {
    super(message);
    Object.setPrototypeOf(this, DatabaseError.prototype);
  }
}
```

### GatewayError

```ts
// errors/GatewayError.ts
export class GatewayError extends Error {
  readonly name = "GatewayError";

  constructor(
    message: string,
    public readonly cause: Error,
    public readonly statusCode?: number,
  ) {
    super(message);
    Object.setPrototypeOf(this, GatewayError.prototype);
  }
}
```

---

## Error Handling at Boundaries

### Repository Error Wrapping

```ts
// repositories/TrackRepository.ts
import { NotFoundError, DatabaseError } from "../errors";

export class TrackRepository {
  async findById(id: string): Promise<Track | null> {
    try {
      const row = await this.db("tracks").where({ id }).first();

      if (!row) {
        return null;
      }

      return this.toDomain(row);
    } catch (error) {
      this.logger.error(`Failed to fetch track ${id}`, error);
      throw new DatabaseError("Failed to fetch track", error instanceof Error ? error : new Error(String(error)));
    }
  }

  async update(id: string, updates: Partial<Track>): Promise<Track> {
    try {
      const [updated] = await this.db("tracks").where({ id }).update(updates).returning("*");

      if (!updated) {
        throw new NotFoundError("Track", id);
      }

      return this.toDomain(updated);
    } catch (error) {
      if (error instanceof NotFoundError) {
        throw error; // Re-throw domain errors
      }

      this.logger.error(`Failed to update track ${id}`, error);
      throw new DatabaseError("Failed to update track", error instanceof Error ? error : new Error(String(error)));
    }
  }
}
```

### Gateway Error Wrapping

```ts
// gateways/CatalogGateway.ts
import { GatewayError, NotFoundError } from "../errors";

export class CatalogGateway implements ICatalogGateway {
  async getEntity(ref: string): Promise<EntityDto> {
    try {
      const response = await this.http.get(`/entities/${ref}`);

      if (!response.data) {
        throw new NotFoundError("Entity", ref);
      }

      return response.data;
    } catch (error) {
      if (error instanceof NotFoundError) {
        throw error;
      }

      const statusCode = (error as any)?.response?.status;

      this.logger.error(`Failed to fetch entity ${ref}`, error);
      throw new GatewayError(
        `Failed to fetch entity ${ref}`,
        error instanceof Error ? error : new Error(String(error)),
        statusCode,
      );
    }
  }
}
```

### Service Error Handling

```ts
// services/TrackService.ts
import { ValidationError, NotFoundError } from "../errors";
import { isTrackActive } from "../domains/track";

export class TrackService {
  async certifyEntity(entityRef: string, trackId: string): Promise<Certification> {
    // Validate input
    if (!entityRef) {
      throw new ValidationError("entityRef", entityRef, "Entity reference is required");
    }

    // Fetch track
    const track = await this.trackRepo.findById(trackId);
    if (!track) {
      throw new NotFoundError("Track", trackId);
    }

    // Validate business rules
    if (!isTrackActive(track)) {
      throw new ValidationError("track", trackId, "Track is not active");
    }

    // Create certification
    return this.certRepo.create({ entityRef, trackId });
  }
}
```

---

## Controller Error Mapping

### HTTP Error Mapper Utility

```ts
// utils/error-mapper.ts
import {
  ValidationError,
  UnauthorizedError,
  ForbiddenError,
  NotFoundError,
  ConflictError,
  DatabaseError,
  GatewayError,
} from "../errors";

export function mapErrorToHttp(error: Error): { status: number; body: any } {
  if (error instanceof ValidationError) {
    return {
      status: 400,
      body: {
        error: {
          name: error.name,
          message: error.message,
          details: { field: error.field, value: error.value },
        },
      },
    };
  }

  if (error instanceof UnauthorizedError) {
    return {
      status: 401,
      body: {
        error: {
          name: error.name,
          message: error.message,
        },
      },
    };
  }

  if (error instanceof ForbiddenError) {
    return {
      status: 403,
      body: {
        error: {
          name: error.name,
          message: error.message,
          details: { resource: error.resource },
        },
      },
    };
  }

  if (error instanceof NotFoundError) {
    return {
      status: 404,
      body: {
        error: {
          name: error.name,
          message: error.message,
          details: {
            resourceType: error.resourceType,
            resourceId: error.resourceId,
          },
        },
      },
    };
  }

  if (error instanceof ConflictError) {
    return {
      status: 409,
      body: {
        error: {
          name: error.name,
          message: error.message,
          details: {
            reason: error.reason,
            conflictingId: error.conflictingId,
          },
        },
      },
    };
  }

  if (error instanceof GatewayError) {
    return {
      status: error.statusCode || 502,
      body: {
        error: {
          name: error.name,
          message: error.message,
        },
      },
    };
  }

  if (error instanceof DatabaseError) {
    return {
      status: 500,
      body: {
        error: {
          name: error.name,
          message: "Internal server error",
        },
      },
    };
  }

  // Unknown error
  return {
    status: 500,
    body: {
      error: {
        name: "InternalServerError",
        message: "An unexpected error occurred",
      },
    },
  };
}
```

### Controller with Error Mapping

```ts
// controllers/TrackController.ts
import { Request, Response } from "express";
import { mapErrorToHttp } from "../utils/error-mapper";

export class TrackController {
  constructor(
    private readonly service: TrackService,
    private readonly logger: LoggerService,
  ) {}

  async certify(req: Request, res: Response): Promise<void> {
    try {
      const { entityRef, trackId } = req.body;

      const cert = await this.service.certifyEntity(entityRef, trackId);

      res.status(200).json({
        data: {
          id: cert.id,
          status: cert.status,
          entityRef: cert.entityRef,
          trackId: cert.trackId,
        },
      });
    } catch (error) {
      this.logger.error("Failed to certify entity", error);

      const { status, body } = mapErrorToHttp(error as Error);
      res.status(status).json(body);
    }
  }
}
```

---

## Response Wrapper Utility

```ts
// utils/response-wrapper.ts
export function wrapSuccess<T>(data: T, message?: string) {
  return {
    data,
    ...(message && { message }),
  };
}

export function wrapError(error: Error) {
  const { status, body } = mapErrorToHttp(error);
  return { status, body };
}
```

---

## Pre-Merge Checklist

- [ ] All domain errors extend `Error`
- [ ] Context fields added to custom errors
- [ ] Errors caught at boundaries (gateway, repository)
- [ ] External errors wrapped in domain errors
- [ ] Controller maps domain errors to HTTP status
- [ ] Error mapping utility created (`mapErrorToHttp`)
- [ ] No stack traces in production error responses
- [ ] Logging at error points with context
