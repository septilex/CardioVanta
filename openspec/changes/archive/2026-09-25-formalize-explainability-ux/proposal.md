# Proposal

## Why

The current Explainability UX for the cardiovascular assessment (Phase 14A) correctly distinguishes between user-facing SHAP attributions and technical Logistic Regression explanations, and its design is intentional. However, to be production-ready, it requires accessibility (a11y) improvements for screen readers, responsive hardening for small mobile viewports, and stricter TypeScript type safety for error handling to ensure a robust user experience.

## What Changes

- **Accessibility**: Add proper ARIA roles (`role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`) to the SHAP explanation visual bars. Ensure the technical LR audit chart has appropriate screen-reader context. Add `aria-hidden="true"` to input code span labels to prevent redundant reading by screen readers.
- **Responsive Hardening**: Convert the fixed widths (`100px`, `60px`) in the SHAP explanation bars to fluid widths or flex bases to prevent overflow or horizontal scrolling on very narrow mobile screens.
- **Type Safety**: Fix the `any` type in the API error catch block (`catch (err: any)`) in `handleSubmit` by typing it correctly (e.g., `catch (err: unknown)`) and narrowing the type.
- **No functional or ML changes**: The core API behavior, model logic, and overall visual design remain exactly the same.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.
*(Note: As this is purely a frontend UX refinement, accessibility fix, and code polish without changing core system requirements or API contracts, this change will set `skip_specs: true` in the configuration.)*

## Impact

- **Affected Code**: `src/app/assessment/page.tsx` (Accessibility and Responsive updates, TypeScript fixes).
- **APIs/Systems**: No changes.
- **Dependencies**: No changes.
