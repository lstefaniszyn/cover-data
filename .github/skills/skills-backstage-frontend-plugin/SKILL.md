---
name: skills-backstage-frontend-plugin
description: Build Backstage frontend plugins with React 18+, Material UI v5, TailwindCSS, VCDK design system, and Storybook-first workflow. Use when (1) Creating/modifying Backstage frontend plugins, (2) Implementing Pages, Containers, Components with Clean Architecture, (3) Choosing UI libraries (MUI v5 for ALL components, VCDK for icons only), (4) Writing Storybook stories with MSW mocks, (5) Using MCP tools for documentation, (6) Styling with VCDK tokens and TailwindCSS, (7) Testing React components.
---

# Backstage Frontend Plugin Development

## Quick Start

- **UI Library Priority:** MUI v5 → TailwindCSS → VCDK Icons
- **Architecture:** Page (routes) → Container (integration) → Component (pure UI)
- **Workflow:** Storybook-first development with MSW mocks
- **Dark Theme:** All UI must work in both light and dark mode — never hardcode colors
- **Documentation:** Use MCP tools for up-to-date API docs

## Component Library Selection

### Priority Order (Critical!)

1. **Material UI v5** (`@mui/material`) — **ALL UI components**
2. **TailwindCSS** — Utility-first styling with VCDK design tokens via CSS variables
3. **VCDK SystemIcon** (`@volvo/vcdk-react/SystemIcon`) — Icons only (1000+ Volvo icons)
4. **Backstage Core** — Page layout components

### When to Use Each

✅ **Always MUI v5 for:** ALL UI components — Button, TextField, Table, Dialog, Modal, Select, Checkbox, Radio, Switch, Tooltip, Chip, Avatar, Badge, Card, Alert, Snackbar, Menu, Tabs, Accordion, Pagination, List, Grid, Paper, Divider, etc. Consult [MUI v5 docs](https://mui.com/material-ui/all-components/) via `mcp_mui-mcp_*` tools.

✅ **Always VCDK for icons:** `<SystemIcon name="calendar" />`

✅ **Always VCDK tokens for colors:** `var(--vcdk-color-primary)`, `var(--vcdk-spacing-6)`

✅ **Always theme-aware colors:** Use `var(--vcdk-*, fallback)` — never hardcode hex values

❌ **Never create custom:** Button, Input, Table, Dialog, or any UI primitive

[See references/vcdk-components.md for component selection guide]
[See references/vcdk-icons-catalog.md for complete VCDK icons catalog (1000+ icons)]

## Architecture Decision Tree

### Is it a Page, Container, or Component?

```
1. Does it have a route in router.tsx?
   → YES → Page (src/pages/<domain>/)

2. Does it render Backstage chrome (Page/Header/Content)?
   → YES → Page (src/pages/)

3. Does it use routing hooks (useParams, useNavigate)?
   → YES → Page (src/pages/)

4. Does it fetch data, check permissions, or coordinate state?
   → YES → Container (src/containers/ or co-located)

5. Can it be fully driven by props and rendered in Storybook?
   → YES → Component (src/components/<domain>/)

6. None of the above?
   → SPLIT the module until it matches rules 1-5
```

[See references/architecture-layers.md for detailed definitions and examples]

## Folder Structure

```
src/
├── pages/               # Route-level compositions (Backstage Page/Header/Content)
│   ├── home/
│   │   ├── HomePage.tsx
│   │   └── HomePage.stories.tsx
│   └── events/
│       ├── EventsListPage.tsx
│       └── CreateEventPage.tsx
├── containers/          # Integration layer (API, permissions, analytics)
│   └── EventsListContainer.tsx
├── components/          # Pure presentational components
│   ├── events/
│   │   ├── EventCard.tsx
│   │   ├── EventCard.stories.tsx
│   │   └── EventsList.tsx
│   └── ui/              # Reusable UI compositions
├── hooks/               # Custom hooks (useEvents, useCreateEvent)
├── api/                 # API clients
├── domain/              # Domain types and validators
└── infrastructure/      # External service implementations
```

## Storybook-First Workflow

### Non-Negotiables

1. Create story BEFORE integrating into Backstage page
2. Cover all states: Default, Loading, Empty, Error
3. Use MSW for API mocking (never call real backends)
4. Export prop types and use `Meta<typeof Component>`
5. Document review evidence in specs/

### Required Setup

```typescript
// .storybook/preview.ts
import '@volvo/vcdk/themes/all-semantic.css';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import type { Preview } from '@storybook/react';

// Map VCDK tokens to MUI theme
const theme = createTheme({
  palette: {
    primary: { main: 'var(--vcdk-color-primary)' },
    secondary: { main: 'var(--vcdk-color-secondary)' },
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
```

### MUI Standard Events

```tsx
import { action } from '@storybook/addon-actions';

// ✅ MUI uses standard React events
<TextField onChange={(e) => action('onChange')(e.target.value)} />
<Select onChange={(e) => action('onChange')(e.target.value)} />
```

[See references/storybook-workflow.md for MSW patterns and story organization]

## Dark Theme Support

All UI code MUST support both light and dark themes. Backstage signals the active theme via `body[data-theme-mode="dark"]`.

### Key Rules

1. **Never hardcode hex colors** — use CSS custom properties with fallbacks
2. **Use `var(--vcdk-*, fallback)`** for all colors (backgrounds, text, borders)
3. **Dialog/Drawer:** Add `PaperProps.sx` with CSS vars (portals don't inherit ThemeProvider)
4. **Native elements:** Ensure `<select>`, `<input>`, `<textarea>` are styled for dark mode
5. **SVG icons:** Use `currentColor` or CSS vars — not hardcoded colors

### Color Pattern

```tsx
// ❌ WRONG — invisible text in dark mode
const style = { color: "#374151", backgroundColor: "#f9fafb" };

// ✅ CORRECT — adapts automatically
const style = {
  color: "var(--vcdk-form-gray700, #374151)",
  backgroundColor: "var(--vcdk-form-gray50, #f9fafb)",
};
```

### Dialog Dark Background

```tsx
<Dialog
  open={open}
  PaperProps={{
    sx: {
      backgroundColor: 'var(--vcdk-color-bg-subtle, #ffffff)',
      color: 'var(--vcdk-color-text, #1a1a1a)',
    },
  }}
>
```

### Infrastructure Files

- `src/theme/ThemeAwareProvider.tsx` — MUI ThemeProvider with MutationObserver
- `src/theme/useVcdkTokens.ts` — CSS custom properties (light + dark palettes)

[See references/dark-theme-guide.md for complete CSS token reference and detailed patterns]

## MCP Tools for Documentation

When uncertain about APIs, use MCP tools instead of guessing:

### Material UI v5

```bash
# Get MUI v5 docs index
mcp_mui-mcp_useMuiDocs({ urlList: ["https://llms.mui.com/material-ui/5.17.1/llms.txt"] })

# Fetch specific component docs
mcp_mui-mcp_fetchDocs({ urls: ["https://mui.com/material-ui/react-button/"] })
```

### Backstage / React / Other Libraries

```bash
# Step 1: Resolve library ID
mcp_context7_resolve-library-id({ libraryName: "backstage" })

# Step 2: Query documentation
mcp_context7_query-docs({ libraryId: "/backstage/backstage", query: "frontend plugin routes" })
```

[See references/mcp-integration.md for complete MCP usage patterns]

## TypeScript Standards

- **Strict mode:** No implicit `any`, exhaustive checks
- **Type imports:** Use `import type { X } from './types'` (not inline `import { type X }`)
- **Named exports:** Prefer named over default exports
- **ES2022 target:** Use native features over polyfills

[See references/typescript-standards.md for detailed guidelines]

## Pre-Merge Checklist

- [ ] All UI imports from `@mui/material` (icons from `@volvo/vcdk-react/SystemIcon`)
- [ ] Zero custom UI primitive components
- [ ] All presentational components have Storybook stories
- [ ] Stories cover: Default, Loading, Empty, Error states
- [ ] MSW mocks used for API data (no real backend calls)
- [ ] Styling uses VCDK tokens (`var(--vcdk-*)`) or TailwindCSS utilities
- [ ] No hardcoded hex colors — all colors use `var(--vcdk-*, fallback)` CSS custom properties
- [ ] Dark theme verified: UI renders correctly in both light and dark mode
- [ ] Dialogs/Drawers have `PaperProps.sx` with CSS var background/color
- [ ] MUI components use standard React events (no custom event handling needed)
- [ ] TypeScript compiles: `yarn tsc --noEmit`
- [ ] Tests pass: `yarn test --no-watch`
- [ ] Architecture layers respected (Page/Container/Component boundaries)

## Reference Files

When you need detailed information, read these reference files:

| Topic                    | Reference File                                                           |
| ------------------------ | ------------------------------------------------------------------------ |
| **Architecture Layers**  | [references/architecture-layers.md](references/architecture-layers.md)   |
| **VCDK Components**      | [references/vcdk-components.md](references/vcdk-components.md)           |
| **Storybook Workflow**   | [references/storybook-workflow.md](references/storybook-workflow.md)     |
| **TypeScript Standards** | [references/typescript-standards.md](references/typescript-standards.md) |
| **MCP Integration**      | [references/mcp-integration.md](references/mcp-integration.md)           |
| **Dark Theme**           | [references/dark-theme-guide.md](references/dark-theme-guide.md)         |

## Development Commands

```bash
# Start Storybook
yarn workspace @volvogroup-internal/plugin-<name> storybook

# TypeScript check
yarn tsc --noEmit

# Run tests
yarn test --no-watch

# Build plugin
yarn workspace @volvogroup-internal/plugin-<name> build
```
