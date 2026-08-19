# VCDK Component Selection

> **Updated 2026-03-13**: Use MUI v5 for ALL UI components. Use VCDK SystemIcon for icons only. All colors must use CSS custom properties for dark theme support.

## Component Library Priority

| Priority | Library                                          | Use For                                                                                                     |
| -------- | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| **1st**  | MUI v5 (`@mui/material`)                         | **ALL UI components** — Buttons, Inputs, Tables, Dialogs, Layouts, Navigation, Feedback, Data Display, etc. |
| **2nd**  | TailwindCSS + VCDK Tokens                        | Styling, layout, spacing, colors via CSS custom properties (light + dark)                                   |
| **3rd**  | VCDK SystemIcon (`@volvo/vcdk-react/SystemIcon`) | **Icons ONLY** — 1000+ Volvo-branded icons                                                                  |

**Rationale:** MUI v5 provides comprehensive, well-tested components with excellent TypeScript support and accessibility.

---

## Dark Theme Compatibility (Critical!)

All UI code must work in both light and dark mode. Backstage signals dark mode via `body[data-theme-mode="dark"]`.

### Color Rules

```tsx
// ❌ NEVER hardcode hex colors
const style = { color: "#374151", backgroundColor: "#ffffff" };

// ✅ ALWAYS use CSS custom properties with fallback
const style = {
  color: "var(--vcdk-form-gray700, #374151)",
  backgroundColor: "var(--vcdk-color-bg, #ffffff)",
};
```

### Key Token Categories

| Category | Example Tokens                                             | Use For                        |
| -------- | ---------------------------------------------------------- | ------------------------------ |
| General  | `--vcdk-color-bg`, `--vcdk-color-text`                     | Page backgrounds, primary text |
| Form     | `--vcdk-form-gray*`, `--vcdk-form-blue*`                   | Form fields, labels, inputs    |
| Status   | `--vcdk-color-text-error`, `--vcdk-color-text-success`     | Feedback colors                |
| Button   | `--vcdk-form-btn-primary`, `--vcdk-form-btn-primary-hover` | Button backgrounds             |

### MUI Dialog/Drawer Portals

MUI portals render outside the plugin's React tree. Always add explicit dark-safe styles:

```tsx
<Dialog
  PaperProps={{
    sx: {
      backgroundColor: "var(--vcdk-color-bg-subtle, #ffffff)",
      color: "var(--vcdk-color-text, #1a1a1a)",
    },
  }}
/>
```

[See references/dark-theme-guide.md for complete token reference and patterns]

---

## MUI v5 Components (Primary Choice)

### Installation

```bash
yarn add @mui/material @emotion/react @emotion/styled
```

### Import Pattern

```tsx
import { Button, TextField, Card, CardContent } from "@mui/material";
```

### Event Handling

MUI uses **standard React events**:

```tsx
<TextField onChange={(e) => setValue(e.target.value)} />
<Select onChange={(e) => setSelected(e.target.value)} />
<Button onClick={() => handleSubmit()}>Submit</Button>
```

### Common MUI Components

| Component                   | Category     | Use Case                  |
| --------------------------- | ------------ | ------------------------- |
| Button                      | Input        | Primary/Secondary actions |
| TextField                   | Input        | Text input fields         |
| Select                      | Input        | Dropdown selection        |
| Checkbox                    | Input        | Multiple choice           |
| Radio, RadioGroup           | Input        | Single choice             |
| Switch                      | Input        | Toggle settings           |
| Table, TableBody, TableCell | Data Display | Tabular data              |
| Card, CardContent           | Layout       | Content containers        |
| Dialog                      | Feedback     | Modals, confirmations     |
| Snackbar                    | Feedback     | Toast notifications       |
| Chip                        | Data Display | Tags, labels              |
| Avatar                      | Data Display | User images               |
| Tooltip                     | Feedback     | Hover hints               |
| Menu, MenuItem              | Navigation   | Context menus             |
| Tabs, Tab                   | Navigation   | Tabbed interfaces         |
| Accordion                   | Layout       | Expandable sections       |
| Grid                        | Layout       | Responsive layouts        |

**Full Catalog:** [MUI v5 Components](https://mui.com/material-ui/all-components/)

---

## VCDK SystemIcon (Icons Only)

### Installation

```bash
yarn add @volvo/vcdk-react @volvo/vcdk @lit/react
```

### Import Pattern

```tsx
import { SystemIcon } from "@volvo/vcdk-react/SystemIcon";
```

### Usage

```tsx
<SystemIcon name="calendar" size="medium" />
<SystemIcon name="check-circle" size="small" />
<SystemIcon name="arrow-right" size="large" />
```

### Common Icons

- **Actions:** `add`, `edit`, `delete`, `check`, `close`, `search`
- **Navigation:** `arrow-left`, `arrow-right`, `arrow-up`, `arrow-down`, `menu`, `home`
- **Status:** `check-circle`, `error-circle`, `warning-triangle`, `info-circle`
- **Media:** `play`, `pause`, `volume`, `image`
- **Communication:** `email`, `phone`, `chat`, `notification`

**Full Icon Catalog:** [VCDK Storybook - SystemIcon](https://developer.designsystem.volvogroup.com/?path=/docs/web-components-system-icon--docs)

---

## VCDK React Components (Legacy Reference)

**Note:** The sections below document VCDK React components for **reference only**. These should ONLY be used for:

1. **Icons** (SystemIcon - primary use case)
2. Special brand-critical components not available in MUI
3. Migration scenarios (legacy code)

**For new development, use MUI v5 components instead.**

### Import Pattern (if needed)

```tsx
// ✅ Correct - Named imports from specific files
import { Button } from "@volvo/vcdk-react/Button";
import { TextField } from "@volvo/vcdk-react/TextField";

// ❌ Wrong - Don't import from index
import { Button } from "@volvo/vcdk-react";
```

### Event Handling (VCDK)

VCDK components use **custom events** with `detail` property:

```tsx
// ✅ Correct - Custom event with detail
<TextField onChange={(e) => setValue(e.detail.value)} />
<Dropdown onSelect={(e) => setSelected(e.detail.value)} />
<Checkbox onChange={(e) => setChecked(e.detail.checked)} />

// ❌ Wrong - DOM event pattern
<TextField onChange={(e) => setValue(e.target.value)} />
```

### TypeScript Types (VCDK)

```tsx
import { Button } from "@volvo/vcdk-react/Button";
import type { Button as ButtonTypes } from "@volvo/vcdk-react/Button";

type ButtonElement = ButtonTypes.Element;
type ButtonProps = ButtonTypes.Props;
```

---

## Decision Rules

### When to Use MUI v5

✅ **ALL UI components** — Buttons, Inputs, Tables, Dialogs, etc.  
✅ Need TypeScript-first components with excellent type inference  
✅ Need accessibility (ARIA, keyboard navigation) out of the box  
✅ Need theming with VCDK design tokens  
✅ Need automatic dark mode support via CSS custom properties

### When to Use VCDK SystemIcon

✅ **Icons only** — Need Volvo-branded icons  
✅ Need consistent icon sizing across the app  
✅ Need SVG icons with semantic names

### When to Use VCDK React Components

⚠️ **Rare cases only:**

- Brand-critical component not in MUI
- Legacy code migration
- Specific Volvo UX requirement

---

## Pre-Merge Checklist

- [ ] All UI components from MUI v5 (not VCDK)
- [ ] Icons use VCDK SystemIcon only
- [ ] MUI event handlers use `e.target.*` pattern
- [ ] No custom Button, Input, Select, Table, or Modal components
- [ ] TypeScript types imported from `@mui/material` (not `@volvo/vcdk-react`)
- [ ] No hardcoded hex colors — all use `var(--vcdk-*, fallback)` CSS custom properties
- [ ] Dialogs/Drawers include `PaperProps.sx` with CSS var background and text color
- [ ] UI verified in both light and dark mode
