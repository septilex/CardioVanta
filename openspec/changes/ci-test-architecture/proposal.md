# Proposal

## Why
The GitHub Actions CI pipeline currently skips the `backend/tests/` suite because the single `pytest tests/` command only targets the ML framework tests. We must ensure every verification layer is executed explicitly and correctly gated before deployment.

## What Changes
- Add explicit `pytest backend/tests/` step in CI.
- Rename `pytest tests/` step for clarity.
- Keep `pip-audit` and `npm audit` blocking.
- Maintain artifact integrity verification.
