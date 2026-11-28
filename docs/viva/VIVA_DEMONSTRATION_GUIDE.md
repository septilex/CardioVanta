# Viva demonstration guide

Use synthetic inputs and metadata only. Start with [setup and verification](SETUP_AND_VERIFICATION.md).
Read the status on each concept before claiming completion. Mocked tests are not live provider/deployment proof.

## 1. LLM API integration

**AI App Engineering — · 0.2 points · Implemented; requires external credentials for live proof**

**Meaning and purpose:** An LLM API consumes derived model output to produce an optional educational explanation. Provider calls are bounded, structured and store=False.

**Open:** [backend/app/ai/client.py](../../backend/app/ai/client.py) — `available, provider_parse, explain`.

**Demonstration and expected behavior:** Run the mocked provider success, timeout and invalid-output tests; configure Redis and OpenAI, request a prediction token, then request its explanation. Replaying a completed token returns 429.

**Automated evidence:** [backend/tests/test_ai_explanation.py](../../backend/tests/test_ai_explanation.py); [backend/tests/test_workspace_security.py](../../backend/tests/test_workspace_security.py); [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py).

**Viva explanation:** “An LLM API consumes derived model output to produce an optional educational explanation. Provider calls are bounded, structured and store=False.”

**Configuration:** LLM_ENABLED=true, OPENAI_API_KEY, OPENAI_MODEL, AI_SIGNING_KEY, REDIS_URL.

**Verification limit:** Shared Redis reservation verified against real Redis (one of 12 concurrent reservations wins). The OpenAI provider itself is mocked; a live call needs the owner's API key.

## 2. Prompt engineering

**AI App Engineering — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Prompt engineering constrains tone, scope and trust boundaries so generated explanations do not become clinical advice.

**Open:** [backend/app/ai/prompts/explanation_v1.py](../../backend/app/ai/prompts/explanation_v1.py) — `SYSTEM, VERSION`.

**Demonstration and expected behavior:** Open SYSTEM alongside provider_parse; inspect the separate system/user messages and the tests for invalid provider responses. Explain why user content cannot replace the system instructions.

**Automated evidence:** [backend/tests/test_ai_explanation.py](../../backend/tests/test_ai_explanation.py).

**Viva explanation:** “Prompt engineering constrains tone, scope and trust boundaries so generated explanations do not become clinical advice.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 3. Structured outputs

**AI App Engineering — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Structured outputs validate provider responses against explicit Pydantic fields and contribution directions before display.

**Open:** [backend/app/ai/schemas.py](../../backend/app/ai/schemas.py) — `ExplanationContent, ExplanationResponse`.

**Demonstration and expected behavior:** Run the valid-response and malformed/direction-mismatch tests; only schema-valid content reaches the browser.

**Automated evidence:** [backend/tests/test_ai_explanation.py](../../backend/tests/test_ai_explanation.py).

**Viva explanation:** “Structured outputs validate provider responses against explicit Pydantic fields and contribution directions before display.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 4. Input sanitization & injection awareness

**Auth & Security — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Input validation rejects unknown fields, malformed values and oversized bodies. Parameterized database operations prevent input from becoming SQL syntax.

**Open:** [backend/app/api/body_limit.py](../../backend/app/api/body_limit.py) — `WorkspaceBodyLimit; PredictRequest in backend/app/schemas/predict.py`.

**Demonstration and expected behavior:** Send a prediction with an extra field and an import with patient_name: expect 422. Send a workspace body over its limit: expect 413 and no parsing/storage.

**Automated evidence:** [backend/tests/test_stage6_security.py](../../backend/tests/test_stage6_security.py); [backend/tests/test_workspace_workflows.py](../../backend/tests/test_workspace_workflows.py).

**Viva explanation:** “Input validation rejects unknown fields, malformed values and oversized bodies. Parameterized database operations prevent input from becoming SQL syntax.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 5. JWT issuance & verification

**Auth & Security — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** JWTs are signed short-lived bearer credentials. The server verifies algorithm, signature, issuer, audience, expiry, not-before and UUID identifiers; refresh credentials rotate as stored hashes.

**Open:** [backend/app/auth/security.py](../../backend/app/auth/security.py) — `issue_access, verify_access, new_session`.

**Demonstration and expected behavior:** Register and call /auth/me. Run altered-signature/claims tests and reuse a consumed refresh token: 401, with session revocation. Specialized explanation tokens remain separate.

**Automated evidence:** [backend/tests/test_workspace_security.py](../../backend/tests/test_workspace_security.py).

**Viva explanation:** “JWTs are signed short-lived bearer credentials. The server verifies algorithm, signature, issuer, audience, expiry, not-before and UUID identifiers; refresh credentials rotate as stored hashes.”

**Configuration:** AUTH_ENABLED, DATABASE_URL, REDIS_URL, JWT_SIGNING_KEY; SQL migration 003; HTTPS APP_ORIGIN and secure cookies in production.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 6. OAuth / 3rd-party login

**Auth & Security — · 0.2 points · Implemented; requires external credentials for live proof**

**Meaning and purpose:** OAuth/OIDC delegates identity verification to Google. Authlib checks state, S256 PKCE and signed ID-token claims; existing email accounts require authenticated linking.

**Open:** [backend/app/api/endpoints/oauth.py](../../backend/app/api/endpoints/oauth.py) — `start, callback, resolve_account`.

**Demonstration and expected behavior:** Run the mocked Google flow with real RSA/nonce validation. Wrong state, nonce, issuer, audience, expiry or signature redirects to a safe failure state; a valid fixture creates a viewer.

**Automated evidence:** [backend/tests/test_workspace_oauth.py](../../backend/tests/test_workspace_oauth.py).

**Viva explanation:** “OAuth/OIDC delegates identity verification to Google. Authlib checks state, S256 PKCE and signed ID-token claims; existing email accounts require authenticated linking.”

**Configuration:** AUTH_ENABLED, DATABASE_URL, REDIS_URL, JWT_SIGNING_KEY; SQL migration 003; HTTPS APP_ORIGIN and secure cookies in production; GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and registered /api/v1/auth/google/callback.

**Verification limit:** State, PKCE, nonce and ID-token checks are tested with real RSA-signed fixtures; no live Google sign-in has been performed (needs the owner's OAuth client).

## 7. Password hashing

**Auth & Security — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Argon2id is a memory-hard password hash with per-password salts; plaintext passwords are never stored. A password change invalidates existing sessions.

**Open:** [backend/app/auth/security.py](../../backend/app/auth/security.py) — `password_hash, password_matches, revoke`.

**Demonstration and expected behavior:** Register, inspect the stored $argon2id$ prefix in a throwaway DB, verify correct/incorrect passwords, then change the password and demonstrate old JWT rejection.

**Automated evidence:** [backend/tests/test_workspace_security.py](../../backend/tests/test_workspace_security.py).

**Viva explanation:** “Argon2id is a memory-hard password hash with per-password salts; plaintext passwords are never stored. A password change invalidates existing sessions.”

**Configuration:** AUTH_ENABLED, DATABASE_URL, REDIS_URL, JWT_SIGNING_KEY; SQL migration 003; HTTPS APP_ORIGIN and secure cookies in production.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 8. Rate limiting

**Auth & Security — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Atomic shared counters enforce limits across processes; Redis TTL bounds each window. Authentication, password changes, imports, checkout, WebSocket connections and AI calls use shared controls.

**Open:** [backend/app/services/shared.py](../../backend/app/services/shared.py) — `LIMIT_SCRIPT, limit, anonymous_id; AI RESERVE_SCRIPT`.

**Demonstration and expected behavior:** Run concurrent attempts: only the configured allowance succeeds, others get 429 with Retry-After. Disconnect Redis: protected work fails closed with 503.

**Automated evidence:** [backend/tests/test_workspace_security.py](../../backend/tests/test_workspace_security.py); [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py).

**Viva explanation:** “Atomic shared counters enforce limits across processes; Redis TTL bounds each window. Authentication, password changes, imports, checkout, WebSocket connections and AI calls use shared controls.”

**Configuration:** REDIS_URL; TEST_REDIS_URL must use dedicated DB 15; CLIENT_IP_HEADER=x-real-ip on Vercel only.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers. Exactly 7 of 40 concurrent attempts succeed. A spoofed X-Forwarded-For through the Compose Next.js proxy was shown to pass through unchanged, so CLIENT_IP_HEADER stays unset there.

## 9. Role-based authorization checks

**Auth & Security — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** RBAC checks authoritative database roles at the backend. Viewer reads, researcher imports/reviews feedback, and admin manages account roles.

**Open:** [backend/app/auth/security.py](../../backend/app/auth/security.py) — `current_user, require_roles`.

**Demonstration and expected behavior:** Call an import route anonymously (401), as viewer (403), then as researcher (allowed). A researcher cannot list admin users; a signed fabricated role claim cannot grant access.

**Automated evidence:** [backend/tests/test_workspace_security.py](../../backend/tests/test_workspace_security.py); [backend/tests/test_workspace_workflows.py](../../backend/tests/test_workspace_workflows.py).

**Viva explanation:** “RBAC checks authoritative database roles at the backend. Viewer reads, researcher imports/reviews feedback, and admin manages account roles.”

**Configuration:** AUTH_ENABLED, DATABASE_URL, REDIS_URL, JWT_SIGNING_KEY; SQL migration 003; HTTPS APP_ORIGIN and secure cookies in production.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 10. Backend deployment

**Backend & System Design — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** A serverless ASGI entry point serves FastAPI while packaging the immutable portable model and runtime dependencies.

**Open:** [api/index.py](../../api/index.py) — `app export; vercel.json rewrites`.

**Demonstration and expected behavior:** Inspect /api rewrites, run deployment configuration and minimal-runtime tests, then GET /api/v1/health locally: status ok. No new Vercel deployment was performed.

**Automated evidence:** [backend/tests/test_r3_deployment.py](../../backend/tests/test_r3_deployment.py); [backend/tests/test_portable_model.py](../../backend/tests/test_portable_model.py).

**Viva explanation:** “A serverless ASGI entry point serves FastAPI while packaging the immutable portable model and runtime dependencies.”

**Configuration:** Vercel project settings for deployment.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 11. File upload handling

**Backend & System Design — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** File handling bounds multipart input, validates every CSV row, and imports only research evaluation metadata inside one transaction.

**Open:** [backend/app/api/endpoints/imports.py](../../backend/app/api/endpoints/imports.py) — `upload; parse_csv and write_rows in services/imports.py`.

**Demonstration and expected behavior:** Sign in as researcher, create an import, submit the header template with approved metadata. Valid rows commit; unknown columns, invalid UTF-8, unsafe filenames and duplicate metrics fail without partial writes.

**Automated evidence:** [backend/tests/test_workspace_workflows.py](../../backend/tests/test_workspace_workflows.py); [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py); [__tests__/workspace.test.tsx](../../__tests__/workspace.test.tsx).

**Viva explanation:** “File handling bounds multipart input, validates every CSV row, and imports only research evaluation metadata inside one transaction.”

**Configuration:** AUTH_ENABLED, DATABASE_URL, REDIS_URL, JWT_SIGNING_KEY; SQL migration 003; HTTPS APP_ORIGIN and secure cookies in production; existing model/cohort records.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers. End to end through the standalone Next.js proxy: upload 200, two rows committed.

## 12. HTTP status codes used correctly

**Backend & System Design — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** HTTP status codes communicate success, validation failure, missing identity, denied access, conflicts, rate limits and unavailable services consistently.

**Open:** [backend/app/main.py](../../backend/app/main.py) — `http_exception_handler; account/import/feedback endpoint responses`.

**Demonstration and expected behavior:** Show 201 registration/import creation, 204 logout, 401 invalid JWT, 403 viewer import, 409 duplicate, 413 body cap, 422 invalid input, 429 quota and 503 unavailable integration.

**Automated evidence:** [backend/tests/test_workspace_workflows.py](../../backend/tests/test_workspace_workflows.py); [backend/tests/test_stage6_security.py](../../backend/tests/test_stage6_security.py).

**Viva explanation:** “HTTP status codes communicate success, validation failure, missing identity, denied access, conflicts, rate limits and unavailable services consistently.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 13. Middleware

**Backend & System Design — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Middleware wraps requests for cross-cutting behavior such as request IDs, monitoring and pre-parser body limits.

**Open:** [backend/app/api/middleware.py](../../backend/app/api/middleware.py) — `MonitoringMiddleware; WorkspaceBodyLimit`.

**Demonstration and expected behavior:** Inspect middleware registration, request ID tests and the oversized auth request test. Bodies exceeding the cap are rejected before endpoint processing.

**Automated evidence:** [tests/test_monitoring.py](../../tests/test_monitoring.py); [backend/tests/test_workspace_workflows.py](../../backend/tests/test_workspace_workflows.py).

**Viva explanation:** “Middleware wraps requests for cross-cutting behavior such as request IDs, monitoring and pre-parser body limits.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 14. Problem modeling

**Backend & System Design — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Problem modeling expresses a fixed 13-feature research prediction contract with explicit outcome and threshold semantics.

**Open:** [backend/app/schemas/predict.py](../../backend/app/schemas/predict.py) — `PredictRequest, PredictResponse; cardiovanta_ml.InferenceEngine`.

**Demonstration and expected behavior:** Submit a synthetic complete profile and inspect probability, feature directions and threshold_status. Missing inputs are rejected; the model artifacts are unchanged.

**Automated evidence:** [backend/tests/test_stage3.py](../../backend/tests/test_stage3.py); [backend/tests/test_r1_feature_contract.py](../../backend/tests/test_r1_feature_contract.py).

**Viva explanation:** “Problem modeling expresses a fixed 13-feature research prediction contract with explicit outcome and threshold semantics.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 15. Request body validation

**Backend & System Design — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Request schemas enforce types, required fields, ranges and forbidden extras before business logic runs.

**Open:** [backend/app/schemas/predict.py](../../backend/app/schemas/predict.py) — `PredictRequest; Credentials, PasswordChange and Checkout models`.

**Demonstration and expected behavior:** Run missing/extra/binary/categorical feature tests and the upload column tests; invalid requests return sanitized 422 responses.

**Automated evidence:** [backend/tests/test_stage2.py](../../backend/tests/test_stage2.py); [backend/tests/test_workspace_workflows.py](../../backend/tests/test_workspace_workflows.py).

**Viva explanation:** “Request schemas enforce types, required fields, ranges and forbidden extras before business logic runs.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 16. RESTful endpoint design

**Backend & System Design — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** REST endpoints represent resources and use HTTP methods for creation, retrieval, updates and deletion.

**Open:** [backend/app/api/endpoints/accounts.py](../../backend/app/api/endpoints/accounts.py) — `register, login, me; imports create_batch/batch_status/upload`.

**Demonstration and expected behavior:** Trace POST /research/imports to an ID, GET that ID, then POST its file. Compare the feedback POST/GET/PATCH/DELETE routes.

**Automated evidence:** [backend/tests/test_workspace_workflows.py](../../backend/tests/test_workspace_workflows.py); [backend/tests/test_workspace_security.py](../../backend/tests/test_workspace_security.py).

**Viva explanation:** “REST endpoints represent resources and use HTTP methods for creation, retrieval, updates and deletion.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 17. Server-side error handling

**Backend & System Design — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Server error handling maps failures to safe responses and rolls back incomplete work without exposing secrets or raw clinical input.

**Open:** [backend/app/main.py](../../backend/app/main.py) — `validation_exception_handler, http_exception_handler; db.orm.session`.

**Demonstration and expected behavior:** Run provider/storage failure tests and sanitized validation logging tests. Verify no connection string or provider payload is returned.

**Automated evidence:** [backend/tests/test_stage6_security.py](../../backend/tests/test_stage6_security.py); [backend/tests/test_secrets_config.py](../../backend/tests/test_secrets_config.py); [backend/tests/test_workspace_workflows.py](../../backend/tests/test_workspace_workflows.py).

**Viva explanation:** “Server error handling maps failures to safe responses and rolls back incomplete work without exposing secrets or raw clinical input.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 18. System design basics: frontend, backend, DB and other systems integration

**Backend & System Design — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** System design separates browser interaction, API authorization, transactional metadata storage, optional shared infrastructure and immutable model inference.

**Open:** [backend/app/main.py](../../backend/app/main.py) — `router composition; src/lib/workspace.ts workspaceRequest`.

**Demonstration and expected behavior:** Follow one import from Workspace through JWT/RBAC to SQL, then its durable status to ImportLive. Explain why prediction serving still starts without database/provider secrets.

**Automated evidence:** [backend/tests/test_portable_model.py](../../backend/tests/test_portable_model.py); [__tests__/workspace.test.tsx](../../__tests__/workspace.test.tsx).

**Viva explanation:** “System design separates browser interaction, API authorization, transactional metadata storage, optional shared infrastructure and immutable model inference.”

**Configuration:** See HLD.md and SETUP_AND_VERIFICATION.md for optional services.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 19. Automated API testing / integration tests

**Engineering Practices — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Automated API tests exercise contracts and failure cases; CI provisions real PostgreSQL, a Mongo replica set and Redis for integration tests.

**Open:** [.github/workflows/verify.yml](../../.github/workflows/verify.yml) — `verify-backend, quarantined-research-tests, verify-frontend`.

**Demonstration and expected behavior:** Run the classified safe pytest suite and Jest. Show local skips explicitly and the CI rules that fail rather than skip when service URLs are missing.

**Automated evidence:** [backend/tests/test_r3_deployment.py](../../backend/tests/test_r3_deployment.py); [backend/tests/test_workspace_security.py](../../backend/tests/test_workspace_security.py); [backend/tests/test_workspace_workflows.py](../../backend/tests/test_workspace_workflows.py); [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py).

**Viva explanation:** “Automated API tests exercise contracts and failure cases; CI provisions real PostgreSQL, a Mongo replica set and Redis for integration tests.”

**Configuration:** Real-service suites verified locally (see 37-49); this branch's CI run happens when it is pushed.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 20. Containerization with Docker

**Engineering Practices — · 0.5 points · Fully implemented and tested**

**Meaning and purpose:** Containers package reproducible application runtimes; Compose supplies health-checked dependencies and persistent local volumes. App processes run as non-root users.

**Open:** [docker-compose.yml](../../docker-compose.yml) — `frontend/backend/postgres/mongo/redis/migrate services`.

**Demonstration and expected behavior:** Run scripts/workspace_setup.py, docker compose --env-file .env.docker config --quiet, then up --build --wait. Verify both health endpoints and import WebSocket behavior.

**Automated evidence:** [.github/workflows/workspace-containers.yml](../../.github/workflows/workspace-containers.yml).

**Viva explanation:** “Containers package reproducible application runtimes; Compose supplies health-checked dependencies and persistent local volumes. App processes run as non-root users.”

**Configuration:** Docker Engine and Compose.

**Verification limit:** Verified in CI on PR #9 (Workspace container verification, run 46130345355): backend, migrate and frontend images built; PostgreSQL, Mongo replica set, Redis, migrations, backend and frontend all reached healthy; /research HTML, /api/v1/health and the proxied /api/v1/auth/status returned successfully.

## 21. Environment variables & secrets management

**Engineering Practices — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Environment configuration separates code from credentials; SecretStr masks values and integrations default to disabled.

**Open:** [backend/app/core/config.py](../../backend/app/core/config.py) — `Settings, SECRET_SETTINGS, require_secret`.

**Demonstration and expected behavior:** Run python -m backend.app.core.config: only presence is reported. Verify .env files are ignored and .env.example contains empty secret values.

**Automated evidence:** [backend/tests/test_secrets_config.py](../../backend/tests/test_secrets_config.py).

**Viva explanation:** “Environment configuration separates code from credentials; SecretStr masks values and integrations default to disabled.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 22. Async data fetching from API

**Frontend — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Async fetching lets the UI await remote results while displaying loading and error states.

**Open:** [src/lib/api.ts](../../src/lib/api.ts) — `prediction API helpers; workspaceRequest in src/lib/workspace.ts`.

**Demonstration and expected behavior:** Submit a synthetic assessment or research import and inspect the network request plus pending, success and failure UI.

**Automated evidence:** [__tests__/encoding-and-coldstart.test.tsx](../../__tests__/encoding-and-coldstart.test.tsx); [__tests__/workspace.test.tsx](../../__tests__/workspace.test.tsx).

**Viva explanation:** “Async fetching lets the UI await remote results while displaying loading and error states.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 23. Client-side routing

**Frontend — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Client-side routing changes App Router pages through Next links while preserving the shared shell.

**Open:** [src/components/shell/AppNav.tsx](../../src/components/shell/AppNav.tsx) — `AppSidebar, MobileNav`.

**Demonstration and expected behavior:** Navigate Research → Workspace → Research or Heart Analysis; inspect active navigation and keyboard-accessible links.

**Automated evidence:** [__tests__/navigation.test.tsx](../../__tests__/navigation.test.tsx).

**Viva explanation:** “Client-side routing changes App Router pages through Next links while preserving the shared shell.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 24. Form handling — controlled inputs

**Frontend — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Controlled inputs keep displayed form values synchronized with React state so validation and submission use the same data.

**Open:** [src/components/research/Workspace.tsx](../../src/components/research/Workspace.tsx) — `Workspace controlled email/password fields`.

**Demonstration and expected behavior:** Type an email and password; show onChange updating state and the exact submitted JSON in the component test.

**Automated evidence:** [__tests__/workspace.test.tsx](../../__tests__/workspace.test.tsx); [__tests__/interactions.test.tsx](../../__tests__/interactions.test.tsx).

**Viva explanation:** “Controlled inputs keep displayed form values synchronized with React state so validation and submission use the same data.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 25. Form validation

**Frontend — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Client validation gives early feedback; backend schemas remain authoritative against bypassed browser controls.

**Open:** [src/components/research/Workspace.tsx](../../src/components/research/Workspace.tsx) — `authenticate and import form`.

**Demonstration and expected behavior:** Create-account inputs require an email and at least 12 password characters; oversized CSV is rejected before import creation. Repeat invalid input directly against the API.

**Automated evidence:** [__tests__/workspace.test.tsx](../../__tests__/workspace.test.tsx); [__tests__/contract.test.ts](../../__tests__/contract.test.ts).

**Viva explanation:** “Client validation gives early feedback; backend schemas remain authoritative against bypassed browser controls.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 26. Frontend deployment

**Frontend — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** A production frontend build produces deployable server HTML, client bundles and static assets for Vercel or the container runtime.

**Open:** [next.config.ts](../../next.config.ts) — `standalone build and response headers`.

**Demonstration and expected behavior:** Run npm run build; show the static routes and the dynamic /research/evaluations route. The live Vercel deployment serves main; this branch was built locally, not deployed.

**Automated evidence:** [backend/tests/test_r3_deployment.py](../../backend/tests/test_r3_deployment.py); `npm run build`.

**Viva explanation:** “A production frontend build produces deployable server HTML, client bundles and static assets for Vercel or the container runtime.”

**Configuration:** Vercel project or Docker runtime for publication.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 27. JavaScript — async/await

**Frontend — · 0.1 points · Fully implemented and tested**

**Meaning and purpose:** async/await expresses nonblocking request sequencing with ordinary try/catch handling.

**Open:** [src/lib/workspace.ts](../../src/lib/workspace.ts) — `workspaceRequest, refreshAccount`.

**Demonstration and expected behavior:** Walk through awaiting batch creation, a scheduling turn and multipart upload; a rejection reaches the visible error message.

**Automated evidence:** [__tests__/workspace.test.tsx](../../__tests__/workspace.test.tsx); [__tests__/async.test.ts](../../__tests__/async.test.ts).

**Viva explanation:** “async/await expresses nonblocking request sequencing with ordinary try/catch handling.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 28. JavaScript — Closures

**Frontend — · 0.1 points · Fully implemented and tested**

**Meaning and purpose:** Closures retain lexical state such as the current batch, reconnect delay and stopped flag across callbacks.

**Open:** [src/components/research/ImportLive.tsx](../../src/components/research/ImportLive.tsx) — `useEffect reconnect, polling and cleanup closures`.

**Demonstration and expected behavior:** Inspect reconnect and the cleanup callback; unmounting closes the captured socket and clears captured timers, proven by the test.

**Automated evidence:** [__tests__/import-live.test.tsx](../../__tests__/import-live.test.tsx); [__tests__/useEffectBehaviour.test.tsx](../../__tests__/useEffectBehaviour.test.tsx).

**Viva explanation:** “Closures retain lexical state such as the current batch, reconnect delay and stopped flag across callbacks.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 29. JavaScript — Event loop

**Frontend — · 0.1 points · Fully implemented and tested**

**Meaning and purpose:** JavaScript runs synchronous work first, Promise microtasks next, then timer tasks. The importer uses this boundary before starting its file request.

**Open:** [src/lib/workspace.ts](../../src/lib/workspace.ts) — `afterStatusUpdate`.

**Demonstration and expected behavior:** Run the real-timer Node test: sync, caller, microtask, timer. React can flush its status update before the timer continuation; a timer turn alone does not guarantee a browser paint.

**Automated evidence:** [__tests__/event-loop.test.ts](../../__tests__/event-loop.test.ts).

**Viva explanation:** “JavaScript runs synchronous work first, Promise microtasks next, then timer tasks. The importer uses this boundary before starting its file request.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 30. JavaScript — Hoisting

**Frontend — · 0.1 points · Fully implemented and tested**

**Meaning and purpose:** Function declarations are initialized before module execution; lexical bindings still have a temporal dead zone.

**Open:** [src/lib/clinicalFormat.ts](../../src/lib/clinicalFormat.ts) — `NO_ESTIMATE, describeEstimate`.

**Demonstration and expected behavior:** Open NO_ESTIMATE calling describeEstimate before its declaration; run the declaration-vs-const hoisting tests and inspect fallback display text.

**Automated evidence:** [__tests__/clinicalFormat.test.ts](../../__tests__/clinicalFormat.test.ts).

**Viva explanation:** “Function declarations are initialized before module execution; lexical bindings still have a temporal dead zone.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 31. JavaScript — Promises vs callbacks

**Frontend — · 0.1 points · Fully implemented and tested**

**Meaning and purpose:** Callbacks provide scheduled continuations; Promises model eventual completion and compose through race/await.

**Open:** [src/lib/async.ts](../../src/lib/async.ts) — `delay, withTimeout`.

**Demonstration and expected behavior:** Follow delay wrapping a timer callback in a Promise, then withTimeout racing the request and clearing its losing timer. Run success, timeout and abort tests.

**Automated evidence:** [__tests__/async.test.ts](../../__tests__/async.test.ts).

**Viva explanation:** “Callbacks provide scheduled continuations; Promises model eventual completion and compose through race/await.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 32. Loading & error UI states

**Frontend — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Loading and error states explain what is happening and how to recover from unavailable services or failed requests.

**Open:** [src/components/research/Workspace.tsx](../../src/components/research/Workspace.tsx) — `loading, busy, error and notice states`.

**Demonstration and expected behavior:** Show account initialization, disabled configuration, incorrect-password error, pending import and a retryable checkout error.

**Automated evidence:** [__tests__/workspace.test.tsx](../../__tests__/workspace.test.tsx); [__tests__/encoding-and-coldstart.test.tsx](../../__tests__/encoding-and-coldstart.test.tsx).

**Viva explanation:** “Loading and error states explain what is happening and how to recover from unavailable services or failed requests.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 33. React component composition

**Frontend — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Component composition reuses the navigation/layout frame while isolating interactive account, import and support behavior.

**Open:** [src/components/shell/DocShell.tsx](../../src/components/shell/DocShell.tsx) — `DocShell composing Workspace, Support and ImportLive`.

**Demonstration and expected behavior:** Open the server page wrapping Workspace in DocShell, then inspect ImportLive as a child receiving batch state and an update callback.

**Automated evidence:** [__tests__/workspace.test.tsx](../../__tests__/workspace.test.tsx); [__tests__/page.test.tsx](../../__tests__/page.test.tsx).

**Viva explanation:** “Component composition reuses the navigation/layout frame while isolating interactive account, import and support behavior.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 34. Responsive layout & styling competence

**Frontend — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Responsive layout adapts spacing, wrapping and form controls to screen size while preserving keyboard focus and readable content.

**Open:** [src/app/workspace.css](../../src/app/workspace.css) — `workspace-page, workspace-form, mobile media query`.

**Demonstration and expected behavior:** Inspect desktop 1440px and mobile 390px screenshots; verify no horizontal overflow and usable input labels. Authenticated screenshots use explicitly synthetic browser fixtures.

**Automated evidence:** [__tests__/workspace.test.tsx](../../__tests__/workspace.test.tsx); [scripts/verify_workspace_ui.cjs](../../scripts/verify_workspace_ui.cjs); [docs/viva/evidence/visual-check.json](../../docs/viva/evidence/visual-check.json).

**Viva explanation:** “Responsive layout adapts spacing, wrapping and form controls to screen size while preserving keyboard focus and readable content.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 35. Side effects with useEffect

**Frontend — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Effects synchronize component lifetimes with external subscriptions and clean up sockets/timers on dependency changes or unmount.

**Open:** [src/components/research/ImportLive.tsx](../../src/components/research/ImportLive.tsx) — `useEffect socket lifecycle`.

**Demonstration and expected behavior:** Run the socket cleanup and polling tests; navigate away during an import and verify the connection and every timer are cleared.

**Automated evidence:** [__tests__/import-live.test.tsx](../../__tests__/import-live.test.tsx); [__tests__/useEffectBehaviour.test.tsx](../../__tests__/useEffectBehaviour.test.tsx).

**Viva explanation:** “Effects synchronize component lifetimes with external subscriptions and clean up sockets/timers on dependency changes or unmount.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 36. State management with useState

**Frontend — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** useState holds changing account, form and import state, triggering render updates through setters.

**Open:** [src/components/research/Workspace.tsx](../../src/components/research/Workspace.tsx) — `Workspace useState values`.

**Demonstration and expected behavior:** Toggle sign-in/create-account, edit fields, select a file and display persisted import completion; each update comes from explicit state.

**Automated evidence:** [__tests__/workspace.test.tsx](../../__tests__/workspace.test.tsx); [__tests__/interactions.test.tsx](../../__tests__/interactions.test.tsx).

**Viva explanation:** “useState holds changing account, form and import state, triggering render updates through setters.”

**Configuration:** None.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 37. Aggregation pipelines

**NoSQL (MongoDB) — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Mongo aggregation groups feedback by section and calculates total/helpful counts without transferring every document to Python.

**Open:** [backend/app/api/endpoints/feedback.py](../../backend/app/api/endpoints/feedback.py) — `feedback_summary`.

**Demonstration and expected behavior:** Create synthetic helpful/unhelpful feedback and GET /feedback/summary; inspect $group, $sum, $cond and $sort.

**Automated evidence:** [backend/tests/test_feedback_crud.py](../../backend/tests/test_feedback_crud.py).

**Viva explanation:** “Mongo aggregation groups feedback by section and calculates total/helpful counts without transferring every document to Python.”

**Configuration:** MONGODB_URI to a replica set; python -m backend.app.db.mongo_setup; TEST_MONGODB_URI for verification.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers.

## 38. CRUD operations (Mongo)

**NoSQL (MongoDB) — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Mongo CRUD persists anonymous votes and allows their owner to update or withdraw them using a one-time returned edit credential.

**Open:** [backend/app/api/endpoints/feedback.py](../../backend/app/api/endpoints/feedback.py) — `create_feedback, read_feedback, update_feedback, delete_feedback`.

**Demonstration and expected behavior:** Create (201), read (200), update with X-Edit-Token (200), delete (204), then read (404). Incorrect tokens cannot modify the record.

**Automated evidence:** [backend/tests/test_feedback_crud.py](../../backend/tests/test_feedback_crud.py); [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py).

**Viva explanation:** “Mongo CRUD persists anonymous votes and allows their owner to update or withdraw them using a one-time returned edit credential.”

**Configuration:** MONGODB_URI to a replica set; python -m backend.app.db.mongo_setup; TEST_MONGODB_URI for verification.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers.

## 39. Embedding vs referencing relationships

**NoSQL (MongoDB) — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Small bounded metadata is embedded for frequent reads; potentially growing audit events reference the parent ObjectId in another collection.

**Open:** [backend/app/db/mongo_setup.py](../../backend/app/db/mongo_setup.py) — `FEEDBACK_SCHEMA.metadata, EVENTS; feedback transaction writes`.

**Demonstration and expected behavior:** Inspect metadata embedded in a feedback document and two referenced create/update events. Delete the parent: a Mongo transaction deletes its events too.

**Automated evidence:** [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py).

**Viva explanation:** “Small bounded metadata is embedded for frequent reads; potentially growing audit events reference the parent ObjectId in another collection.”

**Configuration:** MONGODB_URI to a replica set; python -m backend.app.db.mongo_setup; TEST_MONGODB_URI for verification.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers.

## 40. Indexing for query performance (Mongo)

**NoSQL (MongoDB) — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Compound Mongo indexes support equality filters followed by creation-date ordering, and parent-filtered event history.

**Open:** [backend/app/db/mongo_setup.py](../../backend/app/db/mongo_setup.py) — `setup; research_feedback and research_feedback_events`.

**Demonstration and expected behavior:** Inspect section/date, model-version/date and parent/date indexes; run the explain-plan test. Without any hint, MongoDB's planner chooses the section/date IXSCAN and needs no SORT stage.

**Automated evidence:** [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py).

**Viva explanation:** “Compound Mongo indexes support equality filters followed by creation-date ordering, and parent-filtered event history.”

**Configuration:** MONGODB_URI to a replica set; python -m backend.app.db.mongo_setup; TEST_MONGODB_URI for verification.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers.

## 41. Schema modeling (Mongo)

**NoSQL (MongoDB) — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Database-level JSON Schema enforces types and allowed fields even when a writer bypasses FastAPI. The migration backfills safe metadata and refuses existing invalid documents.

**Open:** [backend/app/db/mongo_setup.py](../../backend/app/db/mongo_setup.py) — `FEEDBACK_SCHEMA, EVENT_SCHEMA, setup`.

**Demonstration and expected behavior:** Run setup twice; insert an invalid section or clinical_input directly with PyMongo and observe WriteError. Valid feedback remains accepted.

**Automated evidence:** [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py).

**Viva explanation:** “Database-level JSON Schema enforces types and allowed fields even when a writer bypasses FastAPI. The migration backfills safe metadata and refuses existing invalid documents.”

**Configuration:** MONGODB_URI to a replica set; python -m backend.app.db.mongo_setup; TEST_MONGODB_URI for verification.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers.

## 42. Filtering, ordering, grouping

**SQL (Postgres) — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** SQL filtering, ordering and grouping turn research records into stable evaluation tables, coverage counts and missing-evaluation lists.

**Open:** [backend/app/db/research.py](../../backend/app/db/research.py) — `VERSION_COVERAGE_SQL, UNEVALUATED_COHORTS_SQL`.

**Demonstration and expected behavior:** Run the three queries after migrations; explain WHERE IS NULL, ORDER BY and GROUP BY. Model versions without evaluations remain visible.

**Automated evidence:** [backend/tests/test_research_db.py](../../backend/tests/test_research_db.py).

**Viva explanation:** “SQL filtering, ordering and grouping turn research records into stable evaluation tables, coverage counts and missing-evaluation lists.”

**Configuration:** DATABASE_URL and migrations 001–003; TEST_DATABASE_URL for verification.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers.

## 43. Indexing for query performance (SQL)

**SQL (Postgres) — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Indexes accelerate actual join/filter and cleanup access paths while uniqueness indexes prevent duplicate identities and metrics.

**Open:** [backend/app/db/sql/001_research_schema.sql](../../backend/app/db/sql/001_research_schema.sql) — `evaluations_model_version_idx, evaluations_cohort_idx; migration 003 session indexes`.

**Demonstration and expected behavior:** Run test_real_postgres_planner_uses_the_declared_indexes: with 20,000 synthetic sessions and batches, PostgreSQL's planner chooses refresh_sessions_expiry_idx for clean-up and upload_batches_owner_idx (no Sort node) for a user's recent imports.

**Automated evidence:** [backend/tests/test_research_db.py](../../backend/tests/test_research_db.py); [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py).

**Viva explanation:** “Indexes accelerate actual join/filter and cleanup access paths while uniqueness indexes prevent duplicate identities and metrics.”

**Configuration:** DATABASE_URL and migrations 001–003; TEST_DATABASE_URL for verification.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers.

## 44. Normalization basics

**SQL (Postgres) — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Normalization separates users, roles, identities and sessions so repeated facts are not copied into unrelated rows.

**Open:** [backend/app/db/sql/003_accounts_operations.sql](../../backend/app/db/sql/003_accounts_operations.sql) — `users, roles, user_roles, oauth_accounts, refresh_sessions`.

**Demonstration and expected behavior:** Trace a user through its role and OAuth mapping, and an evaluation through model/cohort/metrics. Explain why a role change does not rewrite every session.

**Automated evidence:** [backend/tests/test_research_db.py](../../backend/tests/test_research_db.py); [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py).

**Viva explanation:** “Normalization separates users, roles, identities and sessions so repeated facts are not copied into unrelated rows.”

**Configuration:** DATABASE_URL and migrations 001–003; TEST_DATABASE_URL for verification.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers.

## 45. ORM usage (Prisma/Sequelize)

**SQL (Postgres) — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** SQLAlchemy 2 maps Python entities to SQL rows and coordinates identity, relationships and explicit transactions. It is the Python-stack equivalent of the rubric's Prisma/Sequelize examples.

**Open:** [backend/app/db/orm.py](../../backend/app/db/orm.py) — `User, Role, RefreshSession, UploadBatch, SupportPayment, session`.

**Demonstration and expected behavior:** Open registration adding User with Role relationships and session rotation adding RefreshSession. Compare ORM operations with the retained raw research JOIN queries.

**Automated evidence:** [backend/tests/test_workspace_security.py](../../backend/tests/test_workspace_security.py); [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py).

**Viva explanation:** “SQLAlchemy 2 maps Python entities to SQL rows and coordinates identity, relationships and explicit transactions. It is the Python-stack equivalent of the rubric's Prisma/Sequelize examples.”

**Configuration:** DATABASE_URL and migrations 001–003; TEST_DATABASE_URL for verification.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers. Registration, role change, import and refresh rotation ran through the ORM on PostgreSQL.

## 46. Relational schema design with PK/FK

**SQL (Postgres) — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Relational keys give rows stable identity, connect related entities and prevent orphaned or duplicate records.

**Open:** [backend/app/db/sql/003_accounts_operations.sql](../../backend/app/db/sql/003_accounts_operations.sql) — `PRIMARY KEY, REFERENCES, UNIQUE, ON DELETE constraints`.

**Demonstration and expected behavior:** Run migration/FK tests and attempt an orphan metric or role mapping in a transaction: PostgreSQL rejects it.

**Automated evidence:** [backend/tests/test_research_db.py](../../backend/tests/test_research_db.py); [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py).

**Viva explanation:** “Relational keys give rows stable identity, connect related entities and prevent orphaned or duplicate records.”

**Configuration:** DATABASE_URL and migrations 001–003; TEST_DATABASE_URL for verification.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers.

## 47. SQL JOINs

**SQL (Postgres) — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** INNER JOIN returns complete metric provenance; LEFT JOIN preserves models with no evaluations; an anti-join identifies unevaluated cohorts.

**Open:** [backend/app/db/research.py](../../backend/app/db/research.py) — `EVALUATION_TABLE_SQL, VERSION_COVERAGE_SQL, UNEVALUATED_COHORTS_SQL`.

**Demonstration and expected behavior:** Run each query and point out the seeded zero-evaluation model and unevaluated cohorts. Compare why INNER JOIN would hide those gaps.

**Automated evidence:** [backend/tests/test_research_db.py](../../backend/tests/test_research_db.py).

**Viva explanation:** “INNER JOIN returns complete metric provenance; LEFT JOIN preserves models with no evaluations; an anti-join identifies unevaluated cohorts.”

**Configuration:** DATABASE_URL and migrations 001–003; TEST_DATABASE_URL for verification.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers.

## 48. Transactions

**SQL (Postgres) — · 0.2 points · Fully implemented and tested**

**Meaning and purpose:** Transactions make migrations and multi-row imports atomic: either all intended writes commit or none survive.

**Open:** [backend/app/db/migrate.py](../../backend/app/db/migrate.py) — `apply_migrations; imports.upload and services.imports.write_rows`.

**Demonstration and expected behavior:** Run migrations twice, then import a file whose second metric duplicates an existing one. The first new metric must also roll back.

**Automated evidence:** [backend/tests/test_research_db.py](../../backend/tests/test_research_db.py); [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py).

**Viva explanation:** “Transactions make migrations and multi-row imports atomic: either all intended writes commit or none survive.”

**Configuration:** DATABASE_URL and migrations 001–003; TEST_DATABASE_URL for verification.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers.

## 49. Caching with Redis

**System & Integration — · 0.4 points · Fully implemented and tested**

**Meaning and purpose:** Read-through Redis caching avoids repeated public research SQL queries; TTL bounds staleness and successful imports invalidate the cache. No individual predictions are cached.

**Open:** [backend/app/services/shared.py](../../backend/app/services/shared.py) — `cache_read, cache_write, invalidate_research`.

**Demonstration and expected behavior:** GET research evaluations twice (MISS then HIT), import a metric (invalidation), and test expiration. Redis outage falls back to SQL for public reads, while security limits fail closed.

**Automated evidence:** [backend/tests/test_workspace_security.py](../../backend/tests/test_workspace_security.py); [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py).

**Viva explanation:** “Read-through Redis caching avoids repeated public research SQL queries; TTL bounds staleness and successful imports invalidate the cache. No individual predictions are cached.”

**Configuration:** REDIS_URL, RESEARCH_CACHE_TTL; DATABASE_URL.

**Verification limit:** Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis 5.0.14; CI runs the same tests against service containers. End to end: MISS, HIT, import, MISS with the new rows visible.

## 50. Payment gateway integration

**System & Integration — · 0.5 points · Implemented; requires external credentials for live proof**

**Meaning and purpose:** Stripe Checkout handles payment details externally. Only signed test-mode webhook events can mark a support record paid; duplicate event IDs are idempotent.

**Open:** [backend/app/api/endpoints/payments.py](../../backend/app/api/endpoints/payments.py) — `checkout, webhook, record_event`.

**Demonstration and expected behavior:** Run synthetic signed-webhook tests, invalid signatures, repeated delivery and provider failure. With owner test credentials, complete Checkout and verify the Stripe event and PostgreSQL paid record.

**Automated evidence:** [backend/tests/test_workspace_workflows.py](../../backend/tests/test_workspace_workflows.py).

**Viva explanation:** “Stripe Checkout handles payment details externally. Only signed test-mode webhook events can mark a support record paid; duplicate event IDs are idempotent.”

**Configuration:** PAYMENTS_ENABLED=true, sk_test_ STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, DATABASE_URL, REDIS_URL.

**Verification limit:** Mocked Stripe/signature tests pass; no real Stripe test event was processed and no payment is claimed.

## 51. Scheduled jobs / cron

**System & Integration — · 0.3 points · Implemented; deployment verification pending**

**Meaning and purpose:** A protected daily cron removes expired authentication state, marks abandoned import attempts failed and records one idempotent maintenance result per UTC date.

**Open:** [backend/app/api/endpoints/maintenance.py](../../backend/app/api/endpoints/maintenance.py) — `authorize, maintain, daily; vercel.json crons`.

**Demonstration and expected behavior:** Call without the cron bearer secret (401), call with it (completed), and repeat (already_completed). Inspect retained research/feedback and removed expired sessions.

**Automated evidence:** [backend/tests/test_workspace_workflows.py](../../backend/tests/test_workspace_workflows.py); [backend/tests/test_workspace_services.py](../../backend/tests/test_workspace_services.py).

**Viva explanation:** “A protected daily cron removes expired authentication state, marks abandoned import attempts failed and records one idempotent maintenance result per UTC date.”

**Configuration:** CRON_SECRET of at least 32 characters, DATABASE_URL; Vercel production cron at 03:00 UTC / 08:30 Asia/Kolkata.

**Verification limit:** PostgreSQL advisory-lock integration verified: six overlapping invocations on real PostgreSQL produce exactly one run. A scheduled invocation by Vercel has not been observed (requires a deployment with CRON_SECRET).

## 52. Server-side rendering

**System & Integration — · 0.5 points · Fully implemented and tested**

**Meaning and purpose:** Server-side rendering produces HTML on the server for each request. /research/evaluations reads the live research database through the API (cache: no-store) and sends a finished table, so it works without JavaScript and shows an import immediately. /research, by contrast, is prerendered once at build time (SSG) and fetches the same table in the browser.

**Open:** [src/app/research/evaluations/page.tsx](../../src/app/research/evaluations/page.tsx) — `ResearchEvaluationsPage (dynamic = force-dynamic); lib/serverResearch.ts loadEvaluationsOnServer; EvaluationsTable`.

**Demonstration and expected behavior:** npm run build marks /research/evaluations as dynamic and writes no HTML for it. Start the server with RESEARCH_API_ORIGIN, then curl the page twice: two different server timestamps and the database rows in the raw HTML (verified 2026-11-28, including rows imported moments earlier).

**Automated evidence:** [__tests__/ssr-evaluations.test.tsx](../../__tests__/ssr-evaluations.test.tsx); `npm run build`.

**Viva explanation:** “Server-side rendering produces HTML on the server for each request. /research/evaluations reads the live research database through the API (cache: no-store) and sends a finished table, so it works without JavaScript and shows an import immediately. /research, by contrast, is prerendered once at build time (SSG) and fetches the same table in the browser.”

**Configuration:** RESEARCH_API_ORIGIN (server-only) naming the API origin reachable from the Next.js server.

**Verification limit:** Local implementation proof passed; no new deployment claimed.

## 53. WebSocket / real-time communication

**System & Integration — · 0.5 points · Implemented; deployment verification pending**

**Meaning and purpose:** An authenticated WebSocket sends durable import states and heartbeats. Reconnects re-read PostgreSQL, so another serverless instance can resume without an in-memory job registry.

**Open:** [backend/app/api/endpoints/realtime.py](../../backend/app/api/endpoints/realtime.py) — `live, snapshot; src/components/research/ImportLive.tsx (socket + polling fallback)`.

**Demonstration and expected behavior:** Create a batch, connect, send the JWT as the first message and upload metadata. Observe ready then completed; a wrong Origin is refused at the handshake and a bad token is closed 1008. Where sockets are unavailable the page falls back to authenticated polling after three failed connections.

**Automated evidence:** [backend/tests/test_workspace_workflows.py](../../backend/tests/test_workspace_workflows.py); [__tests__/import-live.test.tsx](../../__tests__/import-live.test.tsx); [scripts/verify_workspace_deployment.py](../../scripts/verify_workspace_deployment.py).

**Viva explanation:** “An authenticated WebSocket sends durable import states and heartbeats. Reconnects re-read PostgreSQL, so another serverless instance can resume without an in-memory job registry.”

**Configuration:** AUTH_ENABLED, DATABASE_URL, REDIS_URL, JWT_SIGNING_KEY; SQL migration 003; HTTPS APP_ORIGIN and secure cookies in production; REALTIME_ENABLED=true on a host that can hold WebSocket connections (Docker/uvicorn).

**Verification limit:** Verified 2026-11-28 through the production-shaped stack (standalone Next.js proxy, uvicorn, real PostgreSQL/Redis). Vercel Functions do not host WebSocket servers, so production on Vercel relies on the polling fallback, which is unit-tested but has not been observed on a deployment.
