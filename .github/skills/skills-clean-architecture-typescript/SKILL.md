---
name: skills-clean-architecture-typescript
description: Apply Clean Code principles and Design Patterns to TypeScript projects. Use when (1) Writing or refactoring TypeScript code, (2) Choosing between design patterns (Creational, Structural, Behavioral), (3) Improving code quality and maintainability, (4) Reviewing code against SOLID principles, (5) Deciding architecture patterns for services, repositories, or domain logic. Covers Clean Code (naming, functions, comments), GoF Design Patterns (Factory, Strategy, Observer, etc.), testing principles, and TypeScript-specific best practices.
---

# Clean Architecture & Design Patterns for TypeScript

## Core Objectives (Priority Order)

1. **Correctness** — Behavior is unambiguously right
2. **Clarity** — Competent peer can understand quickly
3. **Simplicity** — Fewest moving parts to achieve goal
4. **Cohesion** — Each unit has single responsibility
5. **Coupling** — Dependencies are explicit and minimal
6. **Testability** — Logic is easy to verify in isolation

## Clean Code Quick Reference

### Naming

✅ **DO:**

- Reveal intent: `getUserEmailAddress()` not `getData()`
- Pronounceable: `customerTimestamp` not `custTmStmp`
- Searchable: `MAX_RETRY_COUNT` not `5`
- Domain terms: `Invoice`, `OrderProcessor`
- Booleans as questions: `isActive`, `hasPermission`, `canEdit`

❌ **AVOID:**

- Abbreviations: `usr`, `calc`, `proc`
- Encodings: `strName`, `iCount`
- Generic: `data`, `info`, `manager`, `handler`

### Functions

✅ **DO:**

- Do one thing well
- Keep small (< 20 lines ideal)
- Few parameters (0-2 ideal, max 3)
- Return results, avoid side effects
- Fail fast with clear messages

❌ **AVOID:**

- Flag parameters (signal multiple responsibilities)
- Hidden side effects
- Multiple levels of abstraction
- Nested conditionals (extract to named functions)

### Comments

✅ **DO:**

- Document WHY, not WHAT
- Explain consequences and trade-offs
- Mark TODOs with ticket references
- Document complex algorithms

❌ **AVOID:**

- Obvious restatements: `// increment i`
- Commented-out code (use Git history)
- Journal comments
- Misleading or outdated comments

[See references/clean-code-principles.md for detailed rules]

## Design Pattern Selection Heuristics

### When to Use Patterns

Before introducing a pattern, verify:

1. **Axis of Change exists** — Real or imminent variability (≥2 strategies, ≥2 families)
2. **Coupling vs. Cohesion improves** — Pattern lowers coupling without harming cohesion
3. **YAGNI passed** — Don't add until diversity is real
4. **Refactor first** — Try simple refactoring before pattern

### Pattern Categories

| Category       | When Object...                              | Examples                    |
| -------------- | ------------------------------------------- | --------------------------- |
| **Creational** | Creation/allocation/initialization varies   | Factory, Builder, Singleton |
| **Structural** | Shape/containment needs runtime composition | Adapter, Decorator, Facade  |
| **Behavioral** | Algorithms/policies vary or needs eventing  | Strategy, Observer, Command |

### Quick Decision Tree

```
Do I have ≥2 algorithms/strategies that vary?
  → YES → Strategy Pattern

Do I need to create families of related objects?
  → YES → Abstract Factory

Do I need to decouple abstraction from implementation (2+ dimensions)?
  → YES → Bridge Pattern

Do I need to add behavior without modifying classes?
  → YES → Decorator Pattern

Do I need to notify multiple objects of state changes?
  → YES → Observer Pattern

Do I need to encapsulate operations as objects?
  → YES → Command Pattern
```

[See references/design-patterns-reference.md for full pattern catalog]

## Common Patterns for TypeScript

### Strategy Pattern

**When:** Multiple algorithms for same task

```typescript
interface PaymentStrategy {
  processPayment(amount: number): Promise<PaymentResult>;
}

class CreditCardPayment implements PaymentStrategy {
  async processPayment(amount: number): Promise<PaymentResult> {
    // Credit card logic
  }
}

class PaymentProcessor {
  constructor(private strategy: PaymentStrategy) {}

  async process(amount: number): Promise<PaymentResult> {
    return this.strategy.processPayment(amount);
  }
}
```

### Factory Pattern

**When:** Object creation logic is complex or varies

```typescript
interface NotificationService {
  send(message: string): Promise<void>;
}

class NotificationFactory {
  static create(type: "email" | "sms" | "push"): NotificationService {
    switch (type) {
      case "email":
        return new EmailService();
      case "sms":
        return new SmsService();
      case "push":
        return new PushService();
      default:
        throw new Error(`Unknown notification type: ${type}`);
    }
  }
}
```

### Repository Pattern

**When:** Abstracting data access

```typescript
interface UserRepository {
  findById(id: string): Promise<User | null>;
  save(user: User): Promise<void>;
  delete(id: string): Promise<void>;
}

class PostgresUserRepository implements UserRepository {
  constructor(private db: Knex) {}

  async findById(id: string): Promise<User | null> {
    const row = await this.db("users").where({ id }).first();
    return row ? this.toDomain(row) : null;
  }
}
```

## Anti-Patterns to Avoid

❌ **God Object** — Class does too many things  
❌ **Blob** — Module with massive responsibilities  
❌ **Lava Flow** — Dead code kept "just in case"  
❌ **Golden Hammer** — Using same pattern everywhere  
❌ **Premature Optimization** — Complex solution before need proven  
❌ **Shotgun Surgery** — One change requires many file edits  
❌ **Feature Envy** — Method uses another class's data excessively

## Testing Principles

### Test Structure

```typescript
describe("OrderProcessor", () => {
  describe("processOrder", () => {
    it("should charge customer and create order record", async () => {
      // Arrange
      const mockPayment = mock<PaymentService>();
      const mockOrderRepo = mock<OrderRepository>();
      const processor = new OrderProcessor(mockPayment, mockOrderRepo);

      // Act
      const result = await processor.processOrder(orderData);

      // Assert
      expect(mockPayment.charge).toHaveBeenCalledWith(orderData.amount);
      expect(result.status).toBe("completed");
    });
  });
});
```

### Testing Heuristics

✅ **DO:**

- Test behavior, not implementation
- One assertion concept per test
- Use builders/factories for test data
- Name tests by behavior: `should X when Y`
- Cover happy path + edge cases + error cases

❌ **AVOID:**

- Testing private methods directly
- Brittle assertions on internal state
- Tests that depend on execution order
- Magic numbers in tests (use named constants)

## SOLID Principles

### Single Responsibility Principle (SRP)

A class should have one reason to change.

### Open/Closed Principle (OCP)

Open for extension, closed for modification.

### Liskov Substitution Principle (LSP)

Subtypes must be substitutable for their base types.

### Interface Segregation Principle (ISP)

Clients shouldn't depend on interfaces they don't use.

### Dependency Inversion Principle (DIP)

Depend on abstractions, not concretions.

[See references/clean-code-principles.md for detailed SOLID examples]

## Pre-Merge Checklist

- [ ] Functions do one thing (< 20 lines ideal)
- [ ] Names reveal intent (no abbreviations)
- [ ] No global state or singletons (unless justified)
- [ ] Dependencies injected, not hardcoded
- [ ] Tests cover happy path + edge cases + errors
- [ ] No commented-out code
- [ ] Pattern choice documented (WHY in PR description)
- [ ] TypeScript strict mode enabled

## Reference Files

| Topic                         | Reference File                                                                     |
| ----------------------------- | ---------------------------------------------------------------------------------- |
| **Clean Code Principles**     | [references/clean-code-principles.md](references/clean-code-principles.md)         |
| **Design Patterns Reference** | [references/design-patterns-reference.md](references/design-patterns-reference.md) |
