# Frontend Architecture Layers

> Clear separation of concerns for React components in Backstage plugins.

## Quick Decision Tree

```
1. Does it render Backstage page chrome (Page/Header/Content)?
   → YES → Page (src/pages/)

2. Does it read/write route state (useParams, useNavigate, query params)?
   → YES → Page (src/pages/)

3. Does it perform integration work (API calls, permissions, analytics)?
   → YES → Container (src/containers/ or co-located)

4. Is it a reusable form field or form composition?
   → YES → Form Component (src/components/ui/)

5. Can it be fully driven by props and is Storybook-ready?
   → YES → Component (src/components/<domain>/)

6. None of the above?
   → SPLIT the module until it matches rules 1-5
```

## Page (`src/pages/<domain>/`)

**Definition:** A navigation boundary that owns page chrome and URL state.

**Rules:**

- **P1.** Mounted by a route in `router.tsx`
- **P2.** Owns Backstage layout wrappers: `Page`, `Header`, `Content`
- **P3.** May use `useParams`, `useNavigate`, `useLocation`, query params
- **P4.** Composes Containers and Components
- **P5.** Coordinates cross-section behavior (e.g., search query affects multiple widgets)

**Example:**

```tsx
// src/pages/event/EventsListPage.tsx
export function EventsListPage(): JSX.Element {
  const navigate = useNavigate();
  const { events, loading, error } = useEventsList();

  return (
    <Page themeId="tool">
      <Header title="Events" />
      <Content>
        <EventsList events={events} onCreateClick={() => navigate("/events/new")} />
      </Content>
    </Page>
  );
}
```

## Container (`src/containers/` or co-located)

**Definition:** Owns exactly one integration responsibility, renders one primary Component.

**Rules:**

- **K1.** Does one of: data fetching, permissions, analytics, state coordination
- **K2.** Renders exactly one root presentational Component
- **K3.** Must NOT render Backstage page chrome (`Page`, `Header`, `Content`)
- **K4.** Must NOT manipulate URL (exception: `*RouteContainer`)
- **K5.** Prefer < 150 LOC

**Allowed Dependencies:**

- Hooks (`useX`), API clients, analytics, permission APIs, config

**Example:**

```tsx
// src/containers/EventsListContainer.tsx
export function EventsListContainer(): JSX.Element {
  const { events, loading, error, refetch } = useEventsList();
  const { captureEvent } = useAnalytics();

  const handleRegister = (eventId: string) => {
    captureEvent("register", "event", { eventId });
    // ... registration logic
  };

  return <EventsList events={events} loading={loading} error={error} onRegister={handleRegister} onRetry={refetch} />;
}
```

## Component (`src/components/<domain>/`)

**Definition:** Pure presentational UI driven entirely by props.

**Rules:**

- **C1.** Inputs come ONLY from props
- **C2.** Outputs go ONLY through callbacks (`onSelect`, `onChange`, `onRetry`)
- **C3.** Must NOT import Backstage layout primitives (`Page`, `Header`, `Content`)
- **C4.** Must NOT use routing hooks (`useNavigate`, `useParams`, `useLocation`)
- **C5.** Must NOT call APIs directly
- **C6.** Must be renderable in Storybook with realistic props

**Allowed Dependencies:**

- MUI v5, local utilities, pure domain types

**Forbidden Dependencies:**

- Router, Backstage plugin APIs, analytics, API clients, config

**Example:**

```tsx
// src/components/event/EventsList/EventsList.tsx
export interface EventsListProps {
  readonly events: EventWithComputed[];
  readonly loading?: boolean;
  readonly error?: string;
  readonly onRegister: (eventId: string) => void;
  readonly onRetry: () => void;
}

export function EventsList({ events, loading, error, onRegister, onRetry }: EventsListProps): JSX.Element {
  if (loading) return <GnLoadingState />;
  if (error) return <GnErrorState message={error} onRetry={onRetry} />;
  if (events.length === 0) return <GnEmptyState title="No events" />;

  return <EventsTable events={events} onRegister={onRegister} />;
}
```

## Form Component (`src/components/ui/`)

**Definition:** Generic, reusable form fields and compositions with `Gn*` prefix.

**Rules:**

- **F1.** Pure presentational (follows all Component rules C1-C6)
- **F2.** Generic and domain-agnostic (not tied to a specific feature)
- **F3.** Prefix with `Gn` (e.g., `GnTextField`, `GnDatePicker`, `GnFilterSidebar`)
- **F4.** Export props type (e.g., `GnTextFieldProps`)
- **F5.** Include Storybook story with title `ui/Gn<ComponentName>`

**Form Component Categories:**
| Category | Components |
|----------|------------|
| **Input Fields** | `GnTextField`, `GnSelectField`, `GnTagsInput`, `GnUrlEditor` |
| **Date/Time** | `GnDatePicker`, `GnTimePicker` |
| **Data Display** | `GnTable`, `GnRow`, `GnCarousel` |
| **Filters** | `GnFilterSidebar` |
| **Media** | `GnImagePicker` |
| **State** | `GnLoadingState`, `GnEmptyState`, `GnErrorState` |
| **Controls** | `GnSubmitBar` |

**Example:**

```tsx
// src/components/ui/GnTextField/GnTextField.tsx
export interface GnTextFieldProps {
  readonly label: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly error?: string;
  readonly required?: boolean;
}

export function GnTextField({ label, value, onChange, error, required }: GnTextFieldProps): JSX.Element {
  return (
    <TextField
      label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      error={Boolean(error)}
      helperText={error}
      required={required}
      fullWidth
    />
  );
}
```

## Router ↔ Pages Alignment

**Critical Rule:** Every route in `router.tsx` MUST point to a Page in `src/pages/`.

```tsx
// router.tsx - CORRECT
import { HomePage } from "./pages/home/HomePage";
import { EventsListPage } from "./pages/event/EventsListPage";

<Routes>
  <Route path="/" element={<HomePage />} />
  <Route path="/events" element={<EventsListPage />} />
</Routes>;
```

**NEVER do this:**

```tsx
// router.tsx - WRONG
import { EventsList } from "./components/EventsList"; // ❌ Component as route
```

## One-Line Litmus Tests

| If changing...              | The module is a... |
| --------------------------- | ------------------ |
| Routing or Backstage layout | **Page**           |
| API shape or analytics      | **Container**      |
| UI look and feel only       | **Component**      |
| Generic form field behavior | **Form Component** |

## Folder Structure Example

```
src/
├── pages/               # Route-level compositions
│   ├── home/
│   │   ├── HomePage.tsx
│   │   └── HomePage.stories.tsx
│   └── events/
│       ├── EventsListPage.tsx
│       └── CreateEventPage.tsx
├── containers/          # Integration layer
│   └── EventsListContainer.tsx
├── components/          # Pure presentational
│   ├── events/
│   │   ├── EventCard.tsx
│   │   ├── EventCard.stories.tsx
│   │   └── EventsList.tsx
│   └── ui/              # Reusable form components
│       ├── GnTextField/
│       └── GnLoadingState/
├── hooks/               # Custom hooks
├── api/                 # API clients
└── domain/              # Domain types
```

## Layer Responsibilities

```
┌───────────────────────────────────────────┐
│  Presentation (Pages/Components)          │
│  - React components, props, events        │
│  - No business logic                      │
└──────────────────┬────────────────────────┘
                   │ calls
┌──────────────────▼────────────────────────┐
│  Application (Hooks & Services)           │
│  - Custom hooks, state management         │
│  - Use case orchestration                 │
└──────────────────┬────────────────────────┘
                   │ uses
┌──────────────────▼────────────────────────┐
│  Domain (Types & Business Rules)          │
│  - Interfaces, validators                 │
│  - Framework-agnostic pure functions      │
└──────────────────┬────────────────────────┘
                   │ defines contracts
┌──────────────────▼────────────────────────┐
│  Infrastructure (API Clients & Adapters)  │
│  - API clients, storage adapters          │
│  - External integrations                  │
└───────────────────────────────────────────┘
```

**Dependency Rules:**

- Outer layers depend on inner layers
- Inner layers NEVER depend on outer layers
- Domain has NO framework imports
