# Tasks

## 1. Accessibility Improvements

- [x] 1.1 Update SHAP explanation (`renderShapExplanation` in `src/app/assessment/page.tsx`) bars with proper ARIA roles (`role="progressbar"`, `aria-valuenow`, etc.) and verify via screen reader or DOM inspection that standard progress semantics are applied.
- [x] 1.2 Update Technical LR explanation (`renderExplanation` in `src/app/assessment/page.tsx`) bars with appropriate screen-reader context (ARIA labels) and verify DOM inspection shows accessible context for chart values.
- [x] 1.3 Add `aria-hidden="true"` to input code span labels in the assessment form and verify the change reduces redundant screen reader output during form navigation.

## 2. Responsive Hardening

- [x] 2.1 Refactor the hardcoded widths (`100px` label, `60px` value) in the SHAP explanation visual bars to use fluid widths, flex-basis, or percentages in `src/app/assessment/page.tsx`, and verify the layout does not overflow or trigger horizontal scrolling on a simulated 320px width viewport.

## 3. TypeScript Type Safety

- [x] 3.1 Fix the `any` type in the API error catch block (`catch (err: any)`) inside `handleSubmit` in `src/app/assessment/page.tsx` by typing it correctly (`unknown`) and using proper type narrowing. Verify `tsc` passes without errors on this file.
- [x] 3.2 Run the full frontend test suite (`npm run test` or `npx jest`) to verify that the UI updates and TypeScript fixes do not break existing test coverage.
