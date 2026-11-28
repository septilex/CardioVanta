# 53-concept implementation matrix

Baseline: origin/main e6b7250 (2026-11-28). In progress; the initial audit is not deployment proof.

| # | Concept | Category | Points | Initial | Final | Existing evidence / planned changes | Tests / final proof |
|---|---|---|---:|---|---|---|---|
| 1 | LLM API integration | AI App Engineering — | 0.2 | PARTIAL | Pending verification | `backend/app/ai/client.py` already integrates OpenAI, but availability is disabled on Vercel. Complete deployment-safe usage control. | Pending |
| 2 | Prompt engineering | AI App Engineering — | 0.2 | FULL | Pending verification | `backend/app/ai/prompts/explanation_v1.py` contains a carefully constrained system prompt. | Pending |
| 3 | Structured outputs | AI App Engineering — | 0.2 | FULL | Pending verification | `backend/app/ai/schemas.py` and `client.py` implement Pydantic structured output parsing. | Pending |
| 4 | Input sanitization & injection awareness | Auth & Security — | 0.2 | FULL | Pending verification | Strict Pydantic schemas, bounded request body, and explicit untrusted-input instructions in the AI prompt. | Pending |
| 5 | JWT issuance & verification | Auth & Security — | 0.2 | PARTIAL | Pending verification | `backend/app/ai/security.py` uses custom HMAC-signed expiring tokens, not standard JWTs. Implement proper JWT authentication. | Pending |
| 6 | OAuth / 3rd-party login | Auth & Security — | 0.2 | MISSING | Pending verification | Implement Google OAuth/OIDC login. | Pending |
| 7 | Password hashing | Auth & Security — | 0.2 | MISSING | Pending verification | Implement secure Argon2id password hashing for application accounts. | Pending |
| 8 | Rate limiting | Auth & Security — | 0.2 | PARTIAL | Pending verification | Existing AI usage quotas use SQLite. Upgrade to shared, deployment-safe rate limiting and cover other protected endpoints. | Pending |
| 9 | Role-based authorization checks | Auth & Security — | 0.2 | MISSING | Pending verification | Implement admin, researcher, and viewer roles with backend authorization checks. | Pending |
| 10 | Backend deployment | Backend & System Design — | 0.2 | FULL | Pending verification | `api/index.py` and `vercel.json` configure the FastAPI serverless application. | Pending |
| 11 | File upload handling | Backend & System Design — | 0.2 | MISSING | Pending verification | Add safe CSV upload and research-metadata import functionality. | Pending |
| 12 | HTTP status codes used correctly | Backend & System Design — | 0.2 | FULL | Pending verification | Existing endpoints use 200, 201, 204, 401, 403, 404, 422, 429, 503 and other appropriate responses. | Pending |
| 13 | Middleware | Backend & System Design — | 0.2 | FULL | Pending verification | `backend/app/api/middleware.py` implements monitoring middleware and request IDs. | Pending |
| 14 | Problem modeling | Backend & System Design — | 0.2 | FULL | Pending verification | Existing 13-feature cardiovascular model, prediction contracts, model registry, and inference engine. | Pending |
| 15 | Request body validation | Backend & System Design — | 0.2 | FULL | Pending verification | Pydantic validation, strict input schemas and validation exception handlers. | Pending |
| 16 | RESTful endpoint design | Backend & System Design — | 0.2 | FULL | Pending verification | Existing prediction, research, AI explanation and feedback endpoints. | Pending |
| 17 | Server-side error handling | Backend & System Design — | 0.2 | FULL | Pending verification | FastAPI exception handling and endpoint-specific error responses. | Pending |
| 18 | System design basics: frontend, backend, DB and other systems integration | Backend & System Design — | 0.2 | FULL | Pending verification | Existing Next.js + FastAPI + MongoDB + PostgreSQL + ML model architecture. | Pending |
| 19 | Automated API testing / integration tests | Engineering Practices — | 0.2 | FULL | Pending verification | Pytest API tests and CI integration tests using PostgreSQL and MongoDB service containers. | Pending |
| 20 | Containerization with Docker | Engineering Practices — | 0.5 | MISSING | Pending verification | Add production-quality Dockerfiles and Docker Compose. | Pending |
| 21 | Environment variables & secrets management | Engineering Practices — | 0.2 | FULL | Pending verification | `.env.example`, `backend/app/core/config.py`, `SecretStr` and environment-based configuration. | Pending |
| 22 | Async data fetching from API | Frontend — | 0.2 | FULL | Pending verification | `src/lib/api.ts`, prediction API and research fetching. | Pending |
| 23 | Client-side routing | Frontend — | 0.2 | FULL | Pending verification | Next.js App Router, navigation links and `usePathname`. | Pending |
| 24 | Form handling — controlled inputs | Frontend — | 0.2 | FULL | Pending verification | Controlled assessment inputs using `useState` and `onChange`. | Pending |
| 25 | Form validation | Frontend — | 0.2 | FULL | Pending verification | Required fields, input constraints and server-side Pydantic validation. | Pending |
| 26 | Frontend deployment | Frontend — | 0.2 | FULL | Pending verification | Existing Vercel deployment. | Pending |
| 27 | JavaScript — async/await | Frontend — | 0.1 | FULL | Pending verification | Async prediction flow and API calls. | Pending |
| 28 | JavaScript — Closures | Frontend — | 0.1 | FULL | Pending verification | Existing callback handlers and React hooks close over component state and values. | Pending |
| 29 | JavaScript — Event loop | Frontend — | 0.1 | PARTIAL | Pending verification | Async callbacks and Promises exist, but an explicit microtask/macrotask demonstration and test are needed. | Pending |
| 30 | JavaScript — Hoisting | Frontend — | 0.1 | FULL | Pending verification | `src/lib/clinicalFormat.ts` and `__tests__/clinicalFormat.test.ts`. | Pending |
| 31 | JavaScript — Promises vs callbacks | Frontend — | 0.1 | FULL | Pending verification | `src/lib/async.ts` and `__tests__/async.test.ts`. | Pending |
| 32 | Loading & error UI states | Frontend — | 0.2 | FULL | Pending verification | Assessment loading, timeout, error and retry states with tests. | Pending |
| 33 | React component composition | Frontend — | 0.2 | FULL | Pending verification | Existing assessment, result panels, navigation and reusable components. | Pending |
| 34 | Responsive layout & styling competence | Frontend — | 0.2 | FULL | Pending verification | Responsive layouts, mobile navigation and component styles. | Pending |
| 35 | Side effects with useEffect | Frontend — | 0.2 | FULL | Pending verification | Existing prediction warm-up, animation and research fetching effects with cleanup tests. | Pending |
| 36 | State management with useState | Frontend — | 0.2 | FULL | Pending verification | Existing assessment state and UI state management. | Pending |
| 37 | Aggregation pipelines | NoSQL (MongoDB) — | 0.2 | FULL | Pending verification | `backend/app/api/endpoints/feedback.py` uses `$group`, `$sum`, `$cond` and `$sort`. | Pending |
| 38 | CRUD operations (Mongo) | NoSQL (MongoDB) — | 0.2 | FULL | Pending verification | Feedback create, read, update and delete endpoints. | Pending |
| 39 | Embedding vs referencing relationships | NoSQL (MongoDB) — | 0.2 | MISSING | Pending verification | Add a meaningful embedded and referenced data model. | Pending |
| 40 | Indexing for query performance (Mongo) | NoSQL (MongoDB) — | 0.2 | MISSING | Pending verification | Add explicit query-supporting indexes and test them. | Pending |
| 41 | Schema modeling (Mongo) | NoSQL (MongoDB) — | 0.2 | PARTIAL | Pending verification | Pydantic models control application data, but MongoDB-level schema validation needs to be added. | Pending |
| 42 | Filtering, ordering, grouping | SQL (Postgres) — | 0.2 | FULL | Pending verification | Existing research queries include `WHERE`, `ORDER BY` and `GROUP BY`. | Pending |
| 43 | Indexing for query performance (SQL) | SQL (Postgres) — | 0.2 | FULL | Pending verification | Explicit indexes exist in `001_research_schema.sql`. | Pending |
| 44 | Normalization basics | SQL (Postgres) — | 0.2 | FULL | Pending verification | Existing separated research tables and relational constraints. | Pending |
| 45 | ORM usage (Prisma/Sequelize) | SQL (Postgres) — | 0.2 | MISSING | Pending verification | Add a suitable ORM integration for the existing Python backend. | Pending |
| 46 | Relational schema design with PK/FK | SQL (Postgres) — | 0.2 | FULL | Pending verification | Existing primary keys, foreign keys, uniqueness and cascade constraints. | Pending |
| 47 | SQL JOINs | SQL (Postgres) — | 0.2 | FULL | Pending verification | `backend/app/db/research.py` contains INNER JOIN, LEFT JOIN and anti-join queries. | Pending |
| 48 | Transactions | SQL (Postgres) — | 0.2 | FULL | Pending verification | `backend/app/db/migrate.py` explicitly uses PostgreSQL transactions. | Pending |
| 49 | Caching with Redis | System & Integration — | 0.4 | MISSING | Pending verification | Implement Redis-backed caching for appropriate non-clinical data. | Pending |
| 50 | Payment gateway integration | System & Integration — | 0.5 | MISSING | Pending verification | Implement a safe Stripe test-mode support payment flow. | Pending |
| 51 | Scheduled jobs / cron | System & Integration — | 0.3 | MISSING | Pending verification | Add a protected scheduled maintenance task using Vercel Cron. | Pending |
| 52 | Server-side rendering | System & Integration — | 0.5 | FULL | Pending verification | Existing Next.js App Router Server Components, including the root layout and research page. | Pending |
| 53 | WebSocket / real-time communication | System & Integration — | 0.5 | MISSING | Pending verification | Implement real-time operational status or research import progress updates. | Pending |
