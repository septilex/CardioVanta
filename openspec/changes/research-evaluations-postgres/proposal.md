# Proposal: Research evaluations in PostgreSQL

## Why
The Research page and model cards quote model-evaluation figures (calibration slope, ROC-AUC, accuracy) as
hand-written text, copied from JSON and Markdown reports. Those figures are relational: each evaluation belongs
to one registered model version and one patient cohort, and has several metrics. Keeping them in PostgreSQL
lets the API answer questions with SQL JOINs, for example "every metric for every version on every cohort" or
"which cohorts have no evaluation yet", and gives the project its first genuine runtime secret
(`DATABASE_URL`).

This reverses, for research metadata only, the 2026-09-25 decision not to add a database
(`openspec/changes/archive/2026-09-25-production-monitoring-foundation/design.md`). That decision was about
prediction serving and patient data, and both stay database-free.

## What Changes
- A schema of four tables (`model_versions`, `cohorts`, `evaluations`, `metrics`) with foreign keys, applied by
  an idempotent migration runner (`python -m backend.app.db.migrate`).
- Seed data taken only from figures already published in the repository's reports.
- `GET /api/v1/research/evaluations`, which runs three JOIN queries and returns the results.
- A Research page section that loads the endpoint and shows the evaluation table.
- Tests against a throwaway PostgreSQL (CI service container); tests that need no database always run.

## Non-goals
- No patient data, clinical inputs, predictions or probabilities are stored. Prediction serving never opens a
  database connection.
- No write endpoints. The data changes only through reviewed migrations.
- No change to the model registry, which stays file-based and checksum-verified.
