# Design Patterns Reference (GoF)

> Based on _Design Patterns: Elements of Reusable Object-Oriented Software_ (Gang of Four). Use patterns **only** when they reduce coupling, make variability explicit, or clarify a domain concept.

## How to Use This Reference

- Treat this as **decision support**, not a checklist to "use a pattern"
- Capture **WHY** a pattern is needed in PR descriptions
- Keep **public APIs minimal**; hide implementation detail
- Regularly **re-evaluate**: remove patterns when variability or complexity disappears

---

## Universal Selection Heuristics

1. **Axis of Change:** Introduce a pattern only if there's an actual or imminent variability (≥2 strategies, ≥2 product families, multiple observers, interchangeable states)
2. **Coupling vs. Cohesion:** Prefer patterns that lower coupling without harming cohesion
3. **Object Lifetimes:** If creation/allocation/initialization varies, consider a **Creational** pattern
4. **Object Structure:** If you compose objects for shape/containment, consider a **Structural** pattern
5. **Behavior Delegation:** If algorithms/policies vary or you need eventing, consider a **Behavioral** pattern
6. **YAGNI Guard:** Don't introduce families/registries/interfaces until diversity is real
7. **Refactor First:** Try refactoring duplication; if complexity persists, introduce a pattern
8. **Test Signal:** If tests require heavy stubbing/mocking for one concern, you may need an explicit role (interface) introduced by a pattern

---

## Creational Patterns

### Abstract Factory

**Intent:** Provide an interface for creating related objects without specifying concrete classes.

**When to Use:**

- Must create **families** of related products that should vary together
- Swap product sets at runtime/config

**Trade-offs:**

- ✅ Uniform creation & consistency across families
- ❌ More indirection and setup

**Watch-outs:**

- Only one concrete family
- Product proliferation without real family constraints

**Testing:**

- Verify family consistency
- Use contract tests per product role

---

### Builder

**Intent:** Separate complex construction from representation; support incremental, readable assembly.

**When to Use:**

- Objects require **multi-step**, conditional, or validated construction

**Trade-offs:**

- ✅ Clearer creation, validates invariants
- ❌ Extra types and ceremony

**Watch-outs:**

- Simple POJOs with 2–3 fields
- Builders persisting beyond creation

**Testing:**

- Scenario matrices for required/optional parts
- Invariant tests

---

### Factory Method

**Intent:** Delegate instantiation to subclasses or dedicated creators.

**When to Use:**

- A class cannot anticipate which concrete to create
- Plugin points

**Trade-offs:**

- ✅ Extensibility
- ❌ May push complexity into hierarchies

**Watch-outs:**

- Only one concrete product
- Factory that never varies

**Testing:**

- Verify selection logic and error paths for unknown types

---

### Prototype

**Intent:** Create new objects by copying a prototype.

**When to Use:**

- Costs of creating are high
- Structure emerges dynamically

**Trade-offs:**

- ✅ Fast cloning
- ❌ Deep/shallow copy hazards

**Watch-outs:**

- Cloning used to avoid proper constructors
- Hidden shared state

**Testing:**

- Clone independence
- Mutation doesn't leak across copies

---

### Singleton

**Intent:** Ensure a class has only one instance and a global access point.

**When to Use:**

- Truly single resource (registry, configuration, process-wide lock)

**Trade-offs:**

- ❌ Hidden coupling, test hardness, lifecycle issues

**Watch-outs:**

- Global mutable state
- Order-dependent tests
- Reconfiguration pain

**Testing:**

- Prefer explicit lifetime management
- Provide a reset or avoid entirely

---

## Structural Patterns

### Adapter

**Intent:** Convert one interface into another clients expect.

**When to Use:**

- Integrating 3rd-party/legacy services with mismatched interfaces

**Trade-offs:**

- ✅ Decouples client
- ❌ Can hide leaky abstractions

**Watch-outs:**

- Business logic drifting into adapters
- Bidirectional adapters

**Testing:**

- Contract tests for the client-expected interface

---

### Bridge

**Intent:** Decouple abstraction from implementation so both can vary independently.

**When to Use:**

- Need to combine **two dimensions of variation** (e.g., shape × renderer)

**Trade-offs:**

- ✅ Flexible layering
- ❌ More moving parts

**Watch-outs:**

- Only one implementation or one abstraction

**Testing:**

- Cross-product matrix tests across both axes

---

### Composite

**Intent:** Treat part-whole hierarchies uniformly.

**When to Use:**

- Trees where clients should ignore differences between leaves and composites

**Trade-offs:**

- ✅ Uniformity
- ❌ Can obscure constraints (e.g., invalid children)

**Watch-outs:**

- Over-general trees
- Complex constraints in runtime checks

**Testing:**

- Validate invariants (acyclic, allowed children)
- Traversal behaviors

---

### Decorator

**Intent:** Add responsibilities to objects dynamically, transparently to clients.

**When to Use:**

- Need optional, combinable behaviors at runtime

**Trade-offs:**

- ✅ Flexible stacking
- ❌ Can become order-sensitive and hard to trace

**Watch-outs:**

- Deep decorator chains
- Decorators altering semantics instead of adding responsibilities

**Testing:**

- Composition tests per combination
- Verify idempotency where expected

---

### Facade

**Intent:** Provide a simplified interface to a subsystem.

**When to Use:**

- Hide complexity
- Stabilize a volatile subsystem

**Trade-offs:**

- ✅ Easier use
- ❌ Risk of leaking advanced features through escape hatches

**Watch-outs:**

- Facade that mirrors the subsystem 1:1
- No simplification

**Testing:**

- Black-box tests on the coarse API
- Subsystem mocked in unit tests

---

### Flyweight

**Intent:** Share objects efficiently to support large numbers of fine-grained instances.

**When to Use:**

- Many similar, immutable objects
- Memory footprint is critical

**Trade-offs:**

- ✅ State partitioning (intrinsic vs extrinsic)
- ❌ Complexity for savings

**Watch-outs:**

- Premature optimization
- Mutable shared instances

**Testing:**

- Memory/perf characterization
- Immutability checks

---

### Proxy

**Intent:** Surrogate controlling access to another object.

**When to Use:**

- Lazy load, remote proxy, protection proxy, caching

**Trade-offs:**

- ✅ Transparent indirection
- ❌ Can hide latency/failure modes

**Watch-outs:**

- Business branching in proxy
- Unbounded caches

**Testing:**

- Latency/failure simulations
- Ensure semantics match the real subject

---

## Behavioral Patterns

### Chain of Responsibility

**Intent:** Pass requests along a chain; each handler decides to process or forward.

**When to Use:**

- Vary processing pipelines or responsibilities dynamically

**Trade-offs:**

- ✅ Flexible routing
- ❌ Debugging order can be hard

**Watch-outs:**

- Implicit coupling via global order
- Handlers with side effects regardless of handling

**Testing:**

- Path coverage for different handlers
- Verify termination conditions

---

### Command

**Intent:** Encapsulate a request as an object.

**When to Use:**

- Queueing, logging, undo/redo, transactional operations

**Trade-offs:**

- ✅ Decoupling with history
- ❌ More types and lifecycle concerns

**Watch-outs:**

- Anemic commands with logic leaking into invokers/receivers

**Testing:**

- Deterministic execution
- Idempotency, undo semantics

---

### Iterator

**Intent:** Sequentially access elements without exposing representation.

**When to Use:**

- Custom traversals or multiple traversal strategies

**Trade-offs:**

- ✅ Encapsulation
- ❌ May add allocation/complexity

**Watch-outs:**

- Wraps built-in iteration with no value

**Testing:**

- Traversal order and termination
- Concurrent modification behavior

---

### Mediator

**Intent:** Centralize complex communications; reduce pairwise coupling.

**When to Use:**

- Many-to-many interactions among peers

**Trade-offs:**

- ✅ Simplifies peers
- ❌ Mediator can become a god-object

**Watch-outs:**

- Business rules accumulating in mediator
- Peers becoming passive

**Testing:**

- Interaction tests
- Ensure mediator remains thin and cohesive

---

### Memento

**Intent:** Capture and externalize object state without exposing internals.

**When to Use:**

- Undo/rollback
- Temporal navigation

**Trade-offs:**

- ✅ Privacy maintained
- ❌ Snapshot costs

**Watch-outs:**

- Storing huge snapshots
- Unclear ownership of snapshots

**Testing:**

- Restore fidelity and lifecycle cleanup

---

### Observer

**Intent:** One-to-many dependency for event notification.

**When to Use:**

- Decouple producers from consumers
- Plug-in event handling

**Trade-offs:**

- ✅ Flexible extensibility
- ❌ Order and back-pressure challenges

**Watch-outs:**

- Tight coupling through event payloads
- Synchronous fan-out causing latency

**Testing:**

- Subscription lifecycle
- Delivery guarantees
- Error isolation

---

### State

**Intent:** Allow an object to alter behavior when its internal state changes.

**When to Use:**

- Complex state machines with cohesive behaviors per state

**Trade-offs:**

- ✅ Removes conditionals
- ❌ Increases type/instance count

**Watch-outs:**

- Too few states or trivial transitions
- Duplicated transitions across states

**Testing:**

- Transition tables
- Invalid transition handling

---

### Strategy

**Intent:** Define a family of algorithms; make them interchangeable.

**When to Use:**

- Replace conditional logic with pluggable policies

**Trade-offs:**

- ✅ Clear extension
- ❌ More objects and selection logic

**Watch-outs:**

- Only one concrete strategy
- Leaking algorithm-specific knobs to clients

**Testing:**

- Contract tests per strategy
- Selection logic tests

---

### Template Method

**Intent:** Define the skeleton of an algorithm, deferring steps to subclasses/hooks.

**When to Use:**

- Fixed workflow with variable steps

**Trade-offs:**

- ✅ Enforces order
- ❌ Inheritance coupling

**Watch-outs:**

- Hook explosion
- Preferring composition but using inheritance

**Testing:**

- Golden path + overridden steps
- Ensure mandatory hooks are enforced

---

### Visitor

**Intent:** Separate algorithms from object structures they operate on.

**When to Use:**

- Stable object structures with many operations that change over time

**Trade-offs:**

- ✅ Easy to add operations
- ❌ Hard to add new element types

**Watch-outs:**

- Unstable hierarchies
- Visitors encoding business rules across modules

**Testing:**

- Matrix across element types × visitors
- Exhaustiveness

---

## Pattern Selection Decision Tree

```
Need to vary...
│
├─ Object creation? → Creational
│   ├─ Families of products? → Abstract Factory
│   ├─ Complex construction? → Builder
│   ├─ Plugin points? → Factory Method
│   ├─ Cloning? → Prototype
│   └─ Single instance? → Singleton (avoid)
│
├─ Object structure? → Structural
│   ├─ Interface mismatch? → Adapter
│   ├─ Two variation axes? → Bridge
│   ├─ Part-whole trees? → Composite
│   ├─ Add responsibilities? → Decorator
│   ├─ Simplify API? → Facade
│   ├─ Memory optimization? → Flyweight
│   └─ Access control? → Proxy
│
└─ Object behavior? → Behavioral
    ├─ Processing pipeline? → Chain of Responsibility
    ├─ Encapsulate request? → Command
    ├─ Custom traversal? → Iterator
    ├─ Complex interactions? → Mediator
    ├─ Capture state? → Memento
    ├─ Event notification? → Observer
    ├─ State machine? → State
    ├─ Algorithm family? → Strategy
    ├─ Algorithm skeleton? → Template Method
    └─ Operations on structure? → Visitor
```

---

## Anti-Patterns & Misuse

- **Pattern-Driven Design:** Forcing patterns where simpler structures work
- **Excess Indirection:** Layers without purpose; "just in case" abstractions
- **God Objects:** Especially in Mediator/Facade/Singleton; split responsibilities
- **Static Singletons:** Hidden dependencies and order-sensitive tests
- **Leaky Adapters/Decorators:** Business rules creeping into structural roles

---

## Pre-Merge Checklist

- [ ] Pattern solves a real variability or coupling problem
- [ ] Alternatives considered and documented
- [ ] Public API is minimal and stable
- [ ] Tests cover correctness, failure modes, and cross-product matrices
- [ ] Removal criteria defined if pattern becomes unnecessary

---

**Rule of thumb:** Start with composition and clear interfaces. Reach for a pattern **only** when a real axis of change and coupling pressure justify the added structure.
