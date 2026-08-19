# Storybook-first Workflow

> Use Storybook as the primary UI development and review surface for new or changed presentational UI.

## Objectives

- Use Storybook as the primary UI development and review surface
- Ensure every UI change has reproducible states (Default/Success, Loading, Empty, Error)
- Keep stories stable targets for review, regression testing, and optional interaction testing
- Generate documentation via Autodocs, driven by typed props and TSDoc

---

## Scope

**Applies to:**

- New or changed React UI in frontend plugins
- New UI states (Empty, loading, error, permission denied, no data)
- Screen-level UI that can be reviewed without running a full Backstage app

**Excludes:**

- Backstage page wrappers that require runtime app context (unless building a "demo app" story with routing and MSW)

---

## Non-negotiables

1. For each new or changed presentational component, create or update a story file **before** integrating into a Backstage page
2. Stories MUST cover relevant UX states (Success, loading, empty, error)
3. Public component props MUST be explicitly typed and documented
4. Storybook review evidence MUST be recorded in `specs/<feature>/plan.md` or `specs/<feature>/tasks.md`
5. Every new component MUST export its prop type. Stories MUST use `Meta<typeof Component>` for Autodocs inference
6. If a story requires data that would normally come from an API, the story MUST use MSW mocks. Do not call real backend services

---

## MUI v5 + VCDK in Storybook

### Required Setup

1. Import VCDK theme CSS once
2. Create MUI theme that maps VCDK design tokens
3. Wrap stories with MUI `ThemeProvider`

**Preview decorator example:**

```ts
// .storybook/preview.ts
import '@volvo/vcdk/themes/all-semantic.css';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import type { Preview } from '@storybook/react';

// Map VCDK tokens to MUI theme
const theme = createTheme({
  palette: {
    primary: {
      main: 'var(--vcdk-color-primary)',
    },
    secondary: {
      main: 'var(--vcdk-color-secondary)',
    },
    background: {
      default: 'var(--vcdk-color-bg)',
      paper: 'var(--vcdk-color-bg)',
    },
    text: {
      primary: 'var(--vcdk-color-text)',
    },
  },
  spacing: 8,
});

const preview: Preview = {
  decorators: [
    (Story) => (
      <ThemeProvider theme={theme}>
        <Story />
      </ThemeProvider>
    ),
  ],
};

export default preview;
```

### MUI Component Events

MUI v5 components use standard React events. No special handling needed:

```tsx
import { action } from '@storybook/addon-actions';

<TextField
  onChange={(e) => action('onChange')(e.target.value)}
/>

<Select
  onChange={(e) => action('onChange')(e.target.value)}
/>
```

---

## Architecture Boundaries

Refer to [architecture-layers.md](./architecture-layers.md) for strict definitions of Page, Container, and Component.

**Quick recap:**

- **Component:** Pure UI, props-driven, no routing, no API calls
- **Container:** Owns data fetching/integration, renders one Component
- **Page:** Route-level, owns Backstage chrome, composes multiple units

---

## File and Folder Conventions

### Feature-based Co-location

```
src/components/<featureName>/ComponentName/
  ComponentName.tsx
  ComponentName.stories.tsx
  ComponentName.mocks.ts
  ComponentName.test.tsx
```

**Example:**

```
src/components/event/EventCard/
  EventCard.tsx
  EventCard.stories.tsx
  EventCard.mocks.ts
```

### Story Title Convention

Use stable story title paths:

- `title: "Components/<featureName>/<ComponentName>"` for presentational components
- `title: "Containers/<featureName>/<ContainerName>"` for container stories
- `title: "Pages/<featureName>/<PageName>"` for page stories
- `title: "ui/Gn<ComponentName>"` for generic form components

**Do not encode implementation details in titles.** Story IDs change and links/tests break.

---

## Prop Typing and Autodocs

### Component File MUST Export Prop Types

```tsx
// ✅ Correct
export interface EventCardProps {
  readonly title: string;
  readonly summary?: string;
  readonly onSelect?: (id: string) => void;
}

export const EventCard = ({ title, summary, onSelect }: EventCardProps) => {
  // ...
};
```

### Autodocs

- Add `tags: ["autodocs"]` in story meta
- Use `argTypes` to provide control types and descriptions
- Prefer story-level `args` and `parameters` over custom docs pages
- Use MDX only when prose and layout are needed beyond Autodocs

---

## Story Structure (CSF3)

### Mandatory State Stories

For any component that can plausibly render these states, create explicit stories:

- `Loading`
- `Empty`
- `Error`
- `Success` (often `Default`)

**Example:**

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { EventList } from "./EventList";

const meta = {
  title: "Components/event/EventList",
  component: EventList,
  tags: ["autodocs"],
} satisfies Meta<typeof EventList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Success: Story = {
  args: {
    events: [
      { id: "1", title: "Event 1", summary: "Summary 1" },
      { id: "2", title: "Event 2", summary: "Summary 2" },
    ],
  },
};

export const Loading: Story = {
  args: {
    loading: true,
  },
};

export const Empty: Story = {
  args: {
    events: [],
  },
};

export const Error: Story = {
  args: {
    error: "Failed to load events",
  },
};
```

---

## MSW for API Mocking

### When to Use MSW

**MUST use MSW:**

- Any story that renders a Container or Page that performs network calls
- Any story that triggers API calls via `fetch`, `axios`, GraphQL, or Backstage API client

**MUST NOT call real backend services:**

- Stories must be deterministic. Do not depend on external systems.

**Do not overuse MSW:**

- For pure Components that are props-driven, mock via props and fixtures in `*.mocks.ts`

### MSW Setup

**Official documentation:** [MSW Storybook Addon](https://storybook.js.org/addons/msw-storybook-addon)

#### 1. Install Dependencies

```bash
yarn add msw msw-storybook-addon -D
```

#### 2. Generate Service Worker

```bash
npx msw init public/
```

This creates `public/mockServiceWorker.js`.

#### 3. Configure Storybook to Serve Worker

In `.storybook/main.ts`:

```ts
staticDirs: ["../public"];
```

#### 4. Initialize MSW Globally

In `.storybook/preview.ts`:

```ts
import type { Preview } from "@storybook/react";
import { initialize, mswLoader } from "msw-storybook-addon";

initialize({ onUnhandledRequest: "warn" });

const preview: Preview = {
  loaders: [mswLoader],
};

export default preview;
```

#### 5. Create Handlers

Create `src/mocks/handlers.ts`:

```ts
import { http, HttpResponse } from "msw";

export const handlers = [
  http.get("/api/sample/items", () => {
    return HttpResponse.json({
      items: [{ id: "item-1", title: "Demo item", description: "Mocked item" }],
    });
  }),

  http.post("/api/events", async ({ request }) => {
    const rawBody = (await request.json()) || {};
    const body = typeof rawBody === "object" && rawBody !== null ? rawBody : {};
    return HttpResponse.json({
      id: "mock-event-123",
      title: body.title || "Untitled Event",
      status: body.status || "Draft",
      ...body,
    });
  }),
];
```

**CRITICAL:** The path in your MSW handler must match **exactly** the path used in your API client. Check browser devtools Network tab if you get 404s.

#### 6. Connect Handlers to Stories

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { handlers } from "../../mocks/handlers";
import { EventListContainer } from "./EventListContainer";

const meta = {
  title: "Containers/Events/EventListContainer",
  component: EventListContainer,
  tags: ["autodocs"],
} satisfies Meta<typeof EventListContainer>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Success: Story = {
  parameters: { msw: { handlers } },
};

export const Error: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("/api/sample/items", () => {
          return HttpResponse.json({ error: "Failed to load" }, { status: 500 });
        }),
      ],
    },
  },
};
```

### Troubleshooting MSW

If you see 404s or unmocked requests:

- **Path Mismatch:** Double-check request path in API client vs MSW handler
- **Network Tab:** Use browser devtools to inspect request URL and method
- **Browser-only:** MSW only intercepts browser JavaScript requests (not direct navigation)
- See [MSW Troubleshooting](https://mswjs.io/docs/faq#why-is-my-request-not-intercepted)

---

## Review and Evidence Recording

After creating or changing stories:

1. Run Storybook for the plugin workspace
2. Capture evidence (URL, screenshot, or short screen recording)
3. Record approver name and evidence link in `specs/<feature>/plan.md` or `specs/<feature>/tasks.md`

**Evidence is mandatory for non-trivial UI changes.**

---

## Validation Checklist

- [ ] Typecheck with `yarn lint` and `yarn test`
- [ ] Run Storybook and open modified stories
- [ ] All relevant states covered (Success, Loading, Empty, Error)
- [ ] MSW handlers match API client paths exactly
- [ ] Autodocs generated with `Meta<typeof Component>`
- [ ] Evidence recorded in plan/tasks
