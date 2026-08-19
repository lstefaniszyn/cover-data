Test Implementation Prompt for React Backstage Plugin
Objective
Increase test coverage from 63.2% to 80-90% by writing meaningful, behavior-focused tests that validate critical functionality and catch real bugs. Every test must provide genuine value - no coverage farming.
Core Testing Principles
What Makes a Test Valuable

Tests user-facing behavior, not implementation details
Validates critical business logic that, if broken, would impact users
Catches edge cases that could cause runtime errors or unexpected behavior
Acts as living documentation - test names clearly describe what the feature does
Provides regression protection for previously discovered bugs

What to AVOID

Testing that a component renders without crashing (unless it's genuinely complex)
Testing React/library internals (e.g., useState calls)
Testing static content that never changes
Testing implementation details like specific function calls
Snapshot tests without assertions on critical content
Tests that pass even when the feature is broken

Specific Testing Requirements

1. Component Testing Priority
   Focus on components that:

Handle user interactions (forms, buttons, filters)
Display dynamic data from APIs
Have conditional rendering logic
Manage complex state
Interface with Backstage APIs or catalog

2. Test Structure
   Use this pattern for clarity and maintainability:
   typescriptdescribe('ComponentName', () => {
   describe('when [specific scenario/context]', () => {
   it('should [expected behavior from user perspective]', () => {
   // Arrange: Set up test data and component
   // Act: Perform user action or trigger event
   // Assert: Verify outcome that user would observe
   });
   });
   });
3. Critical Test Scenarios
   For Data Display Components:

Loading states with actual loading indicators
Error states with user-friendly error messages
Empty states with helpful guidance
Data transformation and formatting
Pagination/infinite scroll boundaries
Sorting and filtering accuracy

For Forms and User Input:

Valid input submission flow
Validation errors for each invalid case
Field interdependencies
Form state persistence (if applicable)
API error handling with retry mechanisms
Debounced/throttled inputs

For Backstage-Specific Components:

Entity provider integration
Catalog API interactions
Permission checks and access control
Config API usage
Error boundaries for plugin isolation
Route parameters and navigation

4. Edge Cases to Test
   typescript// GOOD: Testing actual edge cases
   it('should handle API timeout gracefully and show retry button', async () => {
   // Mock API to timeout
   server.use(
   rest.get('/api/data', (req, res, ctx) => {
   return res(ctx.delay(5000), ctx.status(408));
   })
   );

render(<DataTable />);

await waitFor(() => {
expect(screen.getByText(/Request timeout/i)).toBeInTheDocument();
expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
});
});

// BAD: Pointless test
it('should render', () => {
render(<DataTable />);
expect(screen.getByTestId('data-table')).toBeInTheDocument();
}); 5. Testing Utilities and Patterns
Use React Testing Library effectively:

Query by accessible roles and text users see
Use userEvent for realistic interactions
Wait for async operations with waitFor or findBy
Test accessibility with getByRole, getByLabelText

Mock strategically:

Mock external dependencies (APIs, Backstage context)
Keep mocks close to reality
Use MSW for API mocking when possible
Don't mock what you're testing

6. Coverage Target Strategy
   To reach 80-90% meaningfully:

First wave (63% → 75%): Cover all critical user paths
Second wave (75% → 85%): Add edge cases and error scenarios
Final wave (85% → 90%): Cover complex integrations and remaining business logic

7. Test Naming Convention
   Write test names that describe:

WHO: The user or system
WHAT: The action or condition
OUTCOME: The expected result

Examples:

✅ "should display error message when API returns 404"
✅ "should filter table results when user types in search box"
❌ "should work correctly"
❌ "should update state"

Implementation Instructions

Analyze existing code to identify:

Components with complex logic but no tests
User-facing features without coverage
Error handling paths
Data transformation functions

Prioritize by risk:

High: Payment processing, data mutations, auth flows
Medium: Data display, filtering, navigation
Low: Static content, simple presentational components

Write tests that fail first - ensure they actually test something
Include helpful error messages in assertions:
typescriptexpect(submitButton).toBeDisabled();
// Better:
expect(submitButton, 'Submit button should be disabled when form is invalid').toBeDisabled();

Group related tests and share setup appropriately using beforeEach
Document complex test setups with comments explaining WHY, not what

Quality Checklist
Before committing, ensure each test:

Would fail if the feature breaks
Tests from the user's perspective
Has a clear, descriptive name
Is independent and can run in isolation
Uses realistic test data
Handles async operations properly
Is maintainable and easy to understand

Example Test File Structure
typescript// UserDashboard.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TestApiProvider } from '@backstage/test-utils';
import { UserDashboard } from './UserDashboard';

describe('UserDashboard', () => {
const mockUser = { /_ realistic user data _/ };

describe('when user data loads successfully', () => {
it('should display user projects with proper formatting', async () => {
// Test implementation focusing on what user sees
});

    it('should allow filtering projects by status', async () => {
      // Test actual filtering behavior
    });

});

describe('when user has no projects', () => {
it('should display helpful empty state with action button', () => {
// Test empty state UX
});
});

describe('when API fails', () => {
it('should show error with retry option', async () => {
// Test error recovery flow
});
});
});
Remember: Every test should make the codebase more reliable and maintainable. If a test doesn't prevent bugs or aid understanding, don't write it.
