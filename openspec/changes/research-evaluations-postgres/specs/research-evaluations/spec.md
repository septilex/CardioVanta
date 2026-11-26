# Research evaluations

## ADDED Requirements

### Requirement: Evaluation data is relational and read with JOINs
The system SHALL store model versions, cohorts, evaluations and metrics in PostgreSQL tables linked by foreign
keys, and SHALL read them with SQL JOIN queries.

#### Scenario: Evaluation table
- **WHEN** a client requests `GET /api/v1/research/evaluations` and the database is configured
- **THEN** the response is 200 and lists each metric with its model version, cohort, method and source

#### Scenario: Versions without evaluations
- **WHEN** a registered model version has no evaluation rows
- **THEN** the coverage list still includes it with an evaluation count of 0

### Requirement: No patient data and no effect on prediction serving
The database SHALL hold only research metadata. Prediction requests SHALL NOT open a database connection.

#### Scenario: Database not configured
- **WHEN** `DATABASE_URL` is not set
- **THEN** the research endpoint returns 503 with code `research_database_not_configured` and predictions still work
