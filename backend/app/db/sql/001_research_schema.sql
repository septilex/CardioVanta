-- Research evaluation metadata (openspec/changes/research-evaluations-postgres).
-- No patient data, clinical inputs or predictions are ever stored here.

CREATE TABLE IF NOT EXISTS model_versions (
    id            SERIAL PRIMARY KEY,
    model_id      TEXT NOT NULL,
    version       TEXT NOT NULL,
    serialization TEXT NOT NULL CHECK (serialization IN ('joblib', 'portable_json')),
    calibration   TEXT NOT NULL,
    registered_on DATE NOT NULL,
    UNIQUE (model_id, version)
);

CREATE TABLE IF NOT EXISTS cohorts (
    id         SERIAL PRIMARY KEY,
    code       TEXT NOT NULL UNIQUE,
    name       TEXT NOT NULL,
    country    TEXT NOT NULL,
    n_patients INTEGER NOT NULL CHECK (n_patients > 0),
    role       TEXT NOT NULL CHECK (role IN ('development', 'held_out_test', 'external'))
);

CREATE TABLE IF NOT EXISTS evaluations (
    id               SERIAL PRIMARY KEY,
    model_version_id INTEGER NOT NULL REFERENCES model_versions (id),
    cohort_id        INTEGER NOT NULL REFERENCES cohorts (id),
    method           TEXT NOT NULL,
    evaluated_on     DATE NOT NULL,
    source           TEXT NOT NULL,
    UNIQUE (model_version_id, cohort_id, method)
);

CREATE TABLE IF NOT EXISTS metrics (
    evaluation_id INTEGER NOT NULL REFERENCES evaluations (id) ON DELETE CASCADE,
    metric        TEXT NOT NULL,
    value         NUMERIC(10, 6) NOT NULL,
    PRIMARY KEY (evaluation_id, metric)
);

CREATE INDEX IF NOT EXISTS evaluations_model_version_idx ON evaluations (model_version_id);
CREATE INDEX IF NOT EXISTS evaluations_cohort_idx ON evaluations (cohort_id);
