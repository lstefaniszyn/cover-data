## Description

<!-- Describe your changes in detail -->

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## Related Issues

<!-- Link to related issues: Fixes #123, Relates to #456 -->

---

## Pre-Submission Checklist

### All Changes

- [ ] Code compiles: `yarn tsc --noEmit`
- [ ] Tests pass: `yarn test --no-watch`
- [ ] Linting passes: `yarn lint`
- [ ] Commit messages follow conventional format

### Frontend Changes

- [ ] **MUI v5 Components**: UI imports from `@mui/material` (icons from `@volvo/vcdk-react/SystemIcon`)
- [ ] **VCDK Styling**: Uses design tokens (`var(--vcdk-*)`) or TailwindCSS utilities
- [ ] **MUI Events**: Standard React events (`e.target.value` for MUI components)
- [ ] **Storybook**: Stories use MUI v5 components, MSW for API mocking
- [ ] **Accessibility**: Proper labels, ARIA attributes, keyboard navigation

### Backend Changes

- [ ] **Clean Architecture**: Proper layer separation (Controller → Service → Repository)
- [ ] **Error Handling**: Errors mapped at layer boundaries
- [ ] **Database**: Migrations documented, parameterized queries used
- [ ] **API**: Follows envelope pattern, proper HTTP status codes

---

## UI Component Compliance (Frontend Only)

**Did you introduce new UI components?**

- [ ] N/A - No new UI components
- [ ] Yes - All from `@mui/material` (icons from `@volvo/vcdk-react/SystemIcon`)
- [ ] Exception needed (explain below)

**Did you add custom styling?**

- [ ] N/A - No custom styling
- [ ] Yes - Uses VCDK tokens/TailwindCSS only
- [ ] Exception needed (explain below)

### Exceptions (if any)

<!-- Explain why an exception is needed and get approval before merging -->

---

## Screenshots/Videos (if applicable)

<!-- Add screenshots for UI changes -->

## Testing Instructions

<!-- How to test these changes locally -->

1.
2.
3.

## Additional Notes

<!-- Any additional information reviewers should know -->
