# Design: Research evaluations in PostgreSQL

## Schema
- `model_versions(id, model_id, version, serialization, calibration, registered_on)`, unique `(model_id, version)`.
- `cohorts(id, code, name, country, n_patients, role)`; role is `development`, `held_out_test` or `external`.
- `evaluations(id, model_version_id → model_versions, cohort_id → cohorts, method, evaluated_on, source)`,
  unique `(model_version_id, cohort_id, method)`.
- `metrics(evaluation_id → evaluations ON DELETE CASCADE, metric, value)`, primary key `(evaluation_id, metric)`.
- `schema_migrations(filename, applied_at)` records applied files.

## Queries
1. Evaluation table: `metrics JOIN evaluations JOIN model_versions JOIN cohorts` (inner joins).
2. Validation coverage per version: `model_versions LEFT JOIN evaluations LEFT JOIN cohorts`, grouped, so a version
   with no evaluations (1.1.1, a byte-for-byte parameter export of 1.1.0) still appears with a count of 0.
3. Cohorts never evaluated by a registered version: `cohorts LEFT JOIN evaluations WHERE evaluations.id IS NULL`.

All queries are static SQL with no user input; the endpoint takes no parameters.

## Connection and failure handling
- The connection string comes only from `settings.require_secret("DATABASE_URL")` (SecretStr, never logged).
- `psycopg` is imported lazily inside the database module, so prediction requests never load it.
- One short-lived connection per request (`connect_timeout=5`, read-only transaction), suitable for serverless.
- Not configured → 503 with `code: research_database_not_configured`. Connection or query failure → 503 with
  `code: research_database_unavailable`; the error is logged by type only.

## Seed data and provenance
Every seeded figure is copied from a committed report, recorded in `evaluations.source`:
- `reports/phase2c_final_evaluation.json` (1.0.0 recipe, 61-patient locked test);
- `reports/h2_1_calibration_confirmation.md` (1.0.0 and 1.1.0 recipes, 20 repeats of nested CV on 242 rows).
The Phase 17 external cohorts (Hungary, Long Beach VA) are listed, but evaluated different 9- and 11-input
recipes, not a registered version, so they have no evaluation rows. Query 3 surfaces exactly that gap.
