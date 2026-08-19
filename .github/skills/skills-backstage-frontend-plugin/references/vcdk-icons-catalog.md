# VCDK Icons Catalog

> Complete reference for VCDK SystemIcon — 1000+ Volvo-branded icons for all use cases.

## Overview

**Package:** `@volvo/vcdk-react/SystemIcon` or `@volvo/vcdk-assets`  
**Storybook:** https://developer.designsystem.volvogroup.com/?path=/docs/web-components-system-icon--docs

VCDK provides 1000+ professionally designed icons covering navigation, actions, status indicators, vehicle-specific symbols, and industry-specific graphics.

---

## Installation

```bash
yarn add @volvo/vcdk-react @volvo/vcdk @lit/react
```

---

## Usage

### React Component

```tsx
import { SystemIcon } from "@volvo/vcdk-react/SystemIcon";

<SystemIcon name="add" size="medium" />
<SystemIcon name="calendar" size="small" />
<SystemIcon name="settings" size="large" />
```

### Web Component

```html
<vcdk-system-icon name="alert"></vcdk-system-icon> <vcdk-system-icon name="check" size="medium"></vcdk-system-icon>
```

---

## Icon Sizes

| Size      | Pixels | Use Case                         |
| --------- | ------ | -------------------------------- |
| `small`   | 16px   | Inline icons, table cells        |
| `medium`  | 24px   | Buttons, form labels (default)   |
| `large`   | 32px   | Headers, prominent actions       |
| `x-large` | 48px   | Hero sections, large UI elements |

---

## Icon Categories

### Navigation Icons

**Common Use Cases:** Menus, breadcrumbs, pagination, tabs

| Icon Name              | Description                  |
| ---------------------- | ---------------------------- |
| `arrow-left`           | Back navigation              |
| `arrow-right`          | Forward navigation           |
| `arrow-up`             | Scroll up, sort ascending    |
| `arrow-down`           | Scroll down, sort descending |
| `chevron-left`         | Collapse left, previous      |
| `chevron-right`        | Expand right, next           |
| `chevron-up`           | Collapse up                  |
| `chevron-down`         | Expand down                  |
| `menu`                 | Hamburger menu               |
| `home`                 | Home page navigation         |
| `breadcrumb-separator` | Breadcrumb divider           |

---

### Action Icons

**Common Use Cases:** Buttons, toolbars, context menus

| Icon Name    | Description          |
| ------------ | -------------------- |
| `add`        | Create new item      |
| `add-circle` | Add with emphasis    |
| `edit`       | Edit/modify content  |
| `delete`     | Remove item          |
| `trash`      | Delete permanently   |
| `save`       | Save changes         |
| `download`   | Download file        |
| `upload`     | Upload file          |
| `copy`       | Duplicate content    |
| `cut`        | Cut to clipboard     |
| `paste`      | Paste from clipboard |
| `print`      | Print document       |
| `share`      | Share content        |
| `export`     | Export data          |
| `import`     | Import data          |
| `refresh`    | Reload/refresh       |
| `undo`       | Undo action          |
| `redo`       | Redo action          |

---

### Status Indicators

**Common Use Cases:** Feedback, alerts, notifications

| Icon Name          | Description               |
| ------------------ | ------------------------- |
| `check`            | Success, completed        |
| `check-circle`     | Success with emphasis     |
| `close`            | Close dialog, dismiss     |
| `error`            | Error state               |
| `error-circle`     | Error with emphasis       |
| `warning`          | Warning state             |
| `warning-triangle` | Critical warning          |
| `info`             | Information               |
| `info-circle`      | Information with emphasis |
| `help`             | Help/support              |
| `question`         | Question mark             |
| `notification`     | New notification          |
| `alert`            | Alert indicator           |

---

### Communication Icons

**Common Use Cases:** Contact forms, messaging, social

| Icon Name      | Description    |
| -------------- | -------------- |
| `email`        | Email/message  |
| `phone`        | Phone call     |
| `chat`         | Chat/messaging |
| `comment`      | Comments       |
| `notification` | Notifications  |
| `bell`         | Alert bell     |
| `user`         | User profile   |
| `users`        | Multiple users |
| `team`         | Team/group     |

---

### Search & Filter Icons

**Common Use Cases:** Search bars, filters, sorting

| Icon Name         | Description          |
| ----------------- | -------------------- |
| `search`          | Search functionality |
| `filter`          | Filter options       |
| `sort`            | Sort data            |
| `sort-ascending`  | Sort A-Z, 0-9        |
| `sort-descending` | Sort Z-A, 9-0        |
| `clear`           | Clear filters        |
| `find`            | Find in page         |

---

### Media & Content Icons

**Common Use Cases:** Media players, galleries, documents

| Icon Name  | Description   |
| ---------- | ------------- |
| `play`     | Play media    |
| `pause`    | Pause media   |
| `stop`     | Stop media    |
| `volume`   | Audio volume  |
| `mute`     | Mute audio    |
| `image`    | Image/photo   |
| `gallery`  | Image gallery |
| `file`     | Generic file  |
| `document` | Text document |
| `pdf`      | PDF file      |
| `video`    | Video file    |
| `audio`    | Audio file    |

---

### Settings & Configuration Icons

**Common Use Cases:** Settings panels, admin tools

| Icon Name     | Description          |
| ------------- | -------------------- |
| `settings`    | Settings/preferences |
| `cog`         | Configuration        |
| `gear`        | Mechanical settings  |
| `tools`       | Tools/utilities      |
| `wrench`      | Maintenance          |
| `admin`       | Administrator        |
| `dashboard`   | Dashboard view       |
| `preferences` | User preferences     |

---

### Vehicle-Specific Icons

**Common Use Cases:** Volvo Group applications, fleet management

| Icon Name      | Description          |
| -------------- | -------------------- |
| `truck`        | Truck vehicle        |
| `bus`          | Bus vehicle          |
| `engine`       | Engine component     |
| `trailer`      | Trailer attachment   |
| `construction` | Construction vehicle |
| `marine`       | Marine/boat          |
| `agriculture`  | Agricultural vehicle |
| `wheel`        | Wheel/tire           |
| `fuel`         | Fuel/gas             |
| `battery`      | Battery/electric     |

---

### Date & Time Icons

**Common Use Cases:** Calendars, scheduling, timers

| Icon Name  | Description       |
| ---------- | ----------------- |
| `calendar` | Calendar/date     |
| `date`     | Date picker       |
| `time`     | Time picker       |
| `clock`    | Clock/time        |
| `schedule` | Schedule/agenda   |
| `event`    | Event marker      |
| `deadline` | Deadline/due date |

---

## Finding Icons

### 1. Check VCDK Icon Data

View all available icons:

```bash
cat node_modules/@volvo/vcdk-assets/src/icon-data.json | jq '.icons[].name'
```

### 2. Browse Storybook

Search interactively: https://developer.designsystem.volvogroup.com/?path=/docs/web-components-system-icon--docs

### 3. Search Pattern

Common naming patterns:

- **Action:** `{verb}` (add, edit, delete)
- **Status:** `{state}-circle` (check-circle, error-circle)
- **Direction:** `arrow-{direction}` (arrow-left, arrow-right)
- **Object:** `{noun}` (calendar, user, truck)

---

## Decision Tree: Icon Selection

```
Need an icon?
    │
    ▼
Search VCDK icon catalog
    │
    ├─ Found? → Use SystemIcon
    │
    └─ Not Found?
        │
        ├─ Generic UI icon? → Check MUI icons as fallback
        │
        └─ Highly specialized? → Check with design team
```

---

## Examples

### Button with Icon

```tsx
import { Button } from "@mui/material";
import { SystemIcon } from "@volvo/vcdk-react/SystemIcon";

<Button startIcon={<SystemIcon name="add" size="medium" />}>
  Create Event
</Button>

<Button startIcon={<SystemIcon name="download" size="medium" />}>
  Export
</Button>
```

### Icon Button

```tsx
import { IconButton } from "@mui/material";
import { SystemIcon } from "@volvo/vcdk-react/SystemIcon";

<IconButton>
  <SystemIcon name="edit" size="medium" />
</IconButton>

<IconButton>
  <SystemIcon name="delete" size="medium" />
</IconButton>
```

### Status Indicator

```tsx
import { Chip } from "@mui/material";
import { SystemIcon } from "@volvo/vcdk-react/SystemIcon";

<Chip
  icon={<SystemIcon name="check-circle" size="small" />}
  label="Completed"
  color="success"
/>

<Chip
  icon={<SystemIcon name="warning-triangle" size="small" />}
  label="Pending"
  color="warning"
/>
```

---

## Pre-Merge Checklist

- [ ] All icons use VCDK SystemIcon (not custom SVG)
- [ ] Icon names verified in VCDK catalog
- [ ] Appropriate size chosen (small/medium/large/x-large)
- [ ] Icons have semantic meaning (not decorative only)
- [ ] Accessible labels provided where needed

---

**Full Icon Explorer:** https://developer.designsystem.volvogroup.com/?path=/docs/web-components-system-icon--docs
