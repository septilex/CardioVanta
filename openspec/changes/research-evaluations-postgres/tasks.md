# Tasks

## 1. Database
- [x] 1.1 Schema and seed SQL (`backend/app/db/sql/`), idempotent migration runner with a `schema_migrations`
  table (`python -m backend.app.db.migrate`). Result: the second run applies nothing.
- [x] 1.2 Driver dependency `psycopg[binary]==3.2.3` in api and backend requirements, imported lazily.

## 2. API
- [x] 2.1 Three JOIN queries in `backend/app/db/research.py` (inner joins, LEFT JOIN with GROUP BY, anti-join).
- [x] 2.2 `GET /api/v1/research/evaluations`: 200 with the results; 503 `research_database_not_configured` or
  `research_database_unavailable`, never exposing the connection string.

## 3. Frontend
- [x] 3.1 Research page section (`src/components/research/DatabaseEvaluations.tsx`): loads the endpoint in a
  `useEffect` with abort on unmount; loading, unavailable and ready states.

## 4. Verification
- [x] 4.1 `backend/tests/test_research_db.py`: 6 tests without a database, 7 against a throwaway PostgreSQL
  (13/13 pass locally); `__tests__/databaseEvaluations.test.tsx` (4 tests). Prediction serving verified not to
  import psycopg.
- [x] 4.2 PostgreSQL 16 service container in the `verify-backend` CI job (`TEST_DATABASE_URL`).
