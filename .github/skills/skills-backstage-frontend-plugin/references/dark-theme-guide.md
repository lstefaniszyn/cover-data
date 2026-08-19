# Dark Theme Support Guide

> **Updated 2026-03-13**: All new UI code MUST support both light and dark themes.

## Overview

Backstage supports light and dark themes. The active theme is signaled by the `data-theme-mode` attribute on `<body>`:

- **Light mode:** `<body>` (no attribute or `data-theme-mode="light"`)
- **Dark mode:** `<body data-theme-mode="dark">`

The plugin integrates dark theme via two key infrastructure files:

- `src/theme/ThemeAwareProvider.tsx` — MUI ThemeProvider that reacts to theme changes
- `src/theme/useVcdkTokens.ts` — Injects CSS custom properties for both light and dark palettes

---

## Architecture

### ThemeAwareProvider

Wraps the plugin's route tree. Uses a `MutationObserver` on `document.body` to detect `data-theme-mode` attribute changes and provides the correct MUI theme (light/dark) to all children.

```tsx
// In your plugin's Router component
import { ThemeAwareProvider } from "../theme/ThemeAwareProvider";

export function Router() {
  return (
    <ThemeAwareProvider>
      <Routes>...</Routes>
    </ThemeAwareProvider>
  );
}
```

### useVcdkTokens Hook

Injects a `<style>` element with CSS custom properties. Defines two blocks:

1. `:root { ... }` — Light theme values (default)
2. `body[data-theme-mode='dark'] { ... }` — Dark theme overrides

Also includes global dark mode CSS rules for:

- Native form elements (`<select>`, `<input>`, `<textarea>`)
- MUI Dialog/Drawer paper backgrounds

---

## CSS Custom Properties Reference

### General Purpose Tokens

Use these for page-level and component backgrounds/text:

| Token                         | Light              | Dark                     | Use For               |
| ----------------------------- | ------------------ | ------------------------ | --------------------- |
| `--vcdk-color-bg`             | `#ffffff`          | `#121212`                | Page background       |
| `--vcdk-color-bg-subtle`      | `#f5f5f5`          | `#1e1e1e`                | Card/Paper background |
| `--vcdk-color-bg-hover`       | `rgba(0,0,0,0.02)` | `rgba(255,255,255,0.04)` | Hover states          |
| `--vcdk-color-text`           | `#1a1a1a`          | `#e0e0e0`                | Primary text          |
| `--vcdk-color-text-secondary` | `#666666`          | `#b0b0b0`                | Secondary text        |
| `--vcdk-color-border`         | `rgba(0,0,0,0.12)` | `rgba(255,255,255,0.12)` | Borders               |
| `--vcdk-color-interactive`    | `#1976d2`          | `#90caf9`                | Links, interactive    |
| `--vcdk-color-text-error`     | `#d32f2f`          | `#ef5350`                | Error text            |
| `--vcdk-color-text-success`   | `#4caf50`          | `#66bb6a`                | Success text          |
| `--vcdk-color-text-warning`   | `#e65100`          | `#ffb74d`                | Warning text          |

### Form-Specific Tokens

Use these for form fields, labels, inputs, and buttons:

| Token                           | Light     | Dark      | Use For                 |
| ------------------------------- | --------- | --------- | ----------------------- |
| `--vcdk-form-gray50`            | `#f9fafb` | `#1e1e1e` | Input backgrounds       |
| `--vcdk-form-gray100`           | `#f3f4f6` | `#2a2a2a` | Chip backgrounds        |
| `--vcdk-form-gray200`           | `#e5e7eb` | `#3a3a3a` | Input borders           |
| `--vcdk-form-gray400`           | `#9ca3af` | `#8a8a8a` | Placeholder text, icons |
| `--vcdk-form-gray600`           | `#4b5563` | `#b0b0b0` | Field labels            |
| `--vcdk-form-gray700`           | `#374151` | `#d0d0d0` | Input text, headings    |
| `--vcdk-form-gray900`           | `#111827` | `#f0f0f0` | Strong text             |
| `--vcdk-form-blue600`           | `#2563eb` | `#3b82f6` | Focus rings, links      |
| `--vcdk-form-red600`            | `#dc2626` | `#ef4444` | Required asterisks      |
| `--vcdk-form-white`             | `#ffffff` | `#1e1e1e` | Section backgrounds     |
| `--vcdk-form-btn-primary`       | `#004fbc` | `#3d8ef0` | Primary button bg       |
| `--vcdk-form-btn-primary-hover` | `#003d96` | `#5ea3f7` | Primary button hover    |

---

## Rules for New Components

### 1. Never Hardcode Colors

```tsx
// ❌ WRONG — breaks in dark mode
const style = { color: "#374151", backgroundColor: "#f9fafb" };

// ✅ CORRECT — adapts to theme automatically
const style = {
  color: "var(--vcdk-form-gray700, #374151)",
  backgroundColor: "var(--vcdk-form-gray50, #f9fafb)",
};
```

### 2. Always Provide Fallback Values

```tsx
// ✅ Always include the light-mode hex as fallback
color: "var(--vcdk-color-text, #1a1a1a)";
```

### 3. Use Shared Color Palettes

For form sections, import from the shared `styles.ts` file:

```tsx
import { colors } from "./styles";

// colors.gray700 resolves to 'var(--vcdk-form-gray700, #374151)'
const labelStyle = { color: colors.gray700 };
```

If a component needs its own color palette (like `GnUrlField`), define it using CSS vars:

```tsx
const colors = {
  gray600: "var(--vcdk-form-gray600, #4b5563)",
  gray700: "var(--vcdk-form-gray700, #374151)",
  // ...
};
```

### 4. MUI Dialog/Drawer Dark Backgrounds

MUI Dialogs render via Portal — they don't inherit the plugin's ThemeProvider styles because Backstage uses Emotion with a `v5-` CSS class prefix. Use `PaperProps` to style them:

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

A global CSS rule in `useVcdkTokens.ts` also applies dark backgrounds to `[class*="MuiDialog-paper"]` and `[class*="MuiDrawer-paper"]` via `!important`.

### 5. Native HTML Form Elements

Native `<select>`, `<option>`, `<input type="date">`, and `<textarea>` elements don't inherit MUI theming. Global CSS rules in `useVcdkTokens.ts` handle these:

```css
body[data-theme-mode="dark"] input[type="date"],
body[data-theme-mode="dark"] input[type="time"],
body[data-theme-mode="dark"] textarea {
  color-scheme: dark;
}
```

If you add a new native form element type, add it to `useVcdkTokens.ts`.

### 6. Inline SVG Icons

Use `currentColor` so SVG icons inherit the parent's text color:

```tsx
<svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
  <path d="..." />
</svg>
```

If you need a specific icon color, use a CSS var:

```tsx
style={{ color: 'var(--vcdk-form-gray400, #9ca3af)' }}
```

---

## Adding New CSS Custom Properties

When you need a new theme-aware color not yet defined:

1. **Add the light value** in `:root { ... }` in `useVcdkTokens.ts`
2. **Add the dark value** in `body[data-theme-mode='dark'] { ... }` in `useVcdkTokens.ts`
3. **Use it** via `var(--vcdk-your-token, <light-fallback>)`

**Naming convention:**

- General: `--vcdk-color-<purpose>` (e.g., `--vcdk-color-bg-card`)
- Form: `--vcdk-form-<color><weight>` (e.g., `--vcdk-form-gray400`)

---

## Backstage-Specific Gotchas

### MUI CSS Class Prefix

Backstage uses a `v5-` prefix on MUI CSS class names (e.g., `v5-MuiDialog-paper` not `MuiDialog-paper`). When writing global CSS selectors, use attribute selectors for broad compatibility:

```css
/* ✅ Works regardless of prefix */
body[data-theme-mode="dark"] [class*="MuiDialog-paper"] {
  background-color: var(--vcdk-color-bg-subtle) !important;
}
```

### Emotion Inline Styles

MUI's Emotion CSS-in-JS generates styles that can override CSS custom properties. Use `!important` in global CSS rules when targeting MUI paper elements.

### Portal Components (Dialog, Menu, Popover)

MUI portal components render at `<body>` level, outside the plugin's React tree. They **do** receive CSS custom properties (since those are on `:root` / `body`) but **don't** receive MUI ThemeProvider styles. Always pass explicit `PaperProps.sx` with CSS vars for critical colors.

---

## Testing Dark Theme

### Visual Verification

1. Toggle theme in Backstage Settings → Appearance
2. Check all states: empty forms, filled forms, error states, disabled states
3. Verify text contrast meets WCAG AA (4.5:1 for normal text, 3:1 for large text)

### Automated Checks

```tsx
// Verify computed styles in Playwright
const bgColor = await page.evaluate(() => {
  const el = document.querySelector('[class*="MuiDialog-paper"]');
  return el ? getComputedStyle(el).backgroundColor : null;
});
// In dark mode: expect 'rgb(30, 30, 30)' (#1e1e1e)
```

---

## Pre-Merge Checklist (Dark Theme)

- [ ] No hardcoded hex colors in styles — all use `var(--vcdk-*, fallback)`
- [ ] Dialogs/Drawers have `PaperProps.sx` with CSS var background/color
- [ ] Native form elements covered by global CSS in `useVcdkTokens.ts`
- [ ] SVG icons use `currentColor` or CSS vars for color
- [ ] New CSS properties added to both `:root` and `body[data-theme-mode='dark']`
- [ ] Visual verification in both light and dark mode
- [ ] Text is readable (sufficient contrast) in both themes
