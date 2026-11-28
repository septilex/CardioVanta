"""Render the requested viva matrix/guide from auditable evidence, without inventing deployment proof."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/viva"
records = json.loads((DEST / "concepts.json").read_text(encoding="utf-8"))
evidence = {}


FULL = "FULL"                        # Fully implemented and tested
PARTIAL = "PARTIAL"                  # Partially implemented
DEPLOY = "DEPLOY_PENDING"            # Implemented and tested; deployment verification pending
CREDENTIALS = "NEEDS_CREDENTIALS"    # Implemented and tested with mocks; live proof requires external credentials
MISSING = "NOT_IMPLEMENTED"          # Not implemented
LABELS = {FULL: "Fully implemented and tested", PARTIAL: "Partially implemented",
          DEPLOY: "Implemented; deployment verification pending",
          CREDENTIALS: "Implemented; requires external credentials for live proof", MISSING: "Not implemented"}


def proof(n, source, symbol, tests, meaning, demo, configuration="None", pending="", status=None):
    """`pending` is the verification note. Any note needs an explicitly chosen status, so an outstanding gap can never
    default to FULL; FULL with a note records how the concept was verified."""
    if pending and status is None:
        raise ValueError(f"concept {n}: a verification note needs an explicit status")
    evidence[n] = dict(source=source, symbol=symbol, tests=tests, meaning=meaning, demo=demo,
                       configuration=configuration, pending=pending, final=status or FULL)


SEC = "backend/tests/test_workspace_security.py"
FLOW = "backend/tests/test_workspace_workflows.py"
SERVICES = "backend/tests/test_workspace_services.py"
SQL = "backend/tests/test_research_db.py"
AUTH = "AUTH_ENABLED, DATABASE_URL, REDIS_URL, JWT_SIGNING_KEY; SQL migration 003; HTTPS APP_ORIGIN and secure cookies in production"
PG = "DATABASE_URL and migrations 001–003; TEST_DATABASE_URL for verification"
MONGO = "MONGODB_URI to a replica set; python -m backend.app.db.mongo_setup; TEST_MONGODB_URI for verification"
REAL = ("Verified 2026-11-28 against real disposable PostgreSQL 16.6, MongoDB 7.0.14 (replica set) and Redis "
        "5.0.14; CI runs the same tests against service containers.")

proof(1, "backend/app/ai/client.py", "available, provider_parse, explain", "backend/tests/test_ai_explanation.py; "+SEC+"; "+SERVICES,
      "An LLM API consumes derived model output to produce an optional educational explanation. Provider calls are bounded, structured and store=False.",
      "Run the mocked provider success, timeout and invalid-output tests; configure Redis and OpenAI, request a prediction token, then request its explanation. Replaying a completed token returns 429.",
      "LLM_ENABLED=true, OPENAI_API_KEY, OPENAI_MODEL, AI_SIGNING_KEY, REDIS_URL",
      "Shared Redis reservation verified against real Redis (one of 12 concurrent reservations wins). The OpenAI provider itself is mocked; a live call needs the owner's API key.", CREDENTIALS)
proof(2, "backend/app/ai/prompts/explanation_v1.py", "SYSTEM, VERSION", "backend/tests/test_ai_explanation.py",
      "Prompt engineering constrains tone, scope and trust boundaries so generated explanations do not become clinical advice.",
      "Open SYSTEM alongside provider_parse; inspect the separate system/user messages and the tests for invalid provider responses. Explain why user content cannot replace the system instructions.")
proof(3, "backend/app/ai/schemas.py", "ExplanationContent, ExplanationResponse", "backend/tests/test_ai_explanation.py",
      "Structured outputs validate provider responses against explicit Pydantic fields and contribution directions before display.",
      "Run the valid-response and malformed/direction-mismatch tests; only schema-valid content reaches the browser.")
proof(4, "backend/app/api/body_limit.py", "WorkspaceBodyLimit; PredictRequest in backend/app/schemas/predict.py", "backend/tests/test_stage6_security.py; "+FLOW,
      "Input validation rejects unknown fields, malformed values and oversized bodies. Parameterized database operations prevent input from becoming SQL syntax.",
      "Send a prediction with an extra field and an import with patient_name: expect 422. Send a workspace body over its limit: expect 413 and no parsing/storage.")
proof(5, "backend/app/auth/security.py", "issue_access, verify_access, new_session", SEC,
      "JWTs are signed short-lived bearer credentials. The server verifies algorithm, signature, issuer, audience, expiry, not-before and UUID identifiers; refresh credentials rotate as stored hashes.",
      "Register and call /auth/me. Run altered-signature/claims tests and reuse a consumed refresh token: 401, with session revocation. Specialized explanation tokens remain separate.", AUTH)
proof(6, "backend/app/api/endpoints/oauth.py", "start, callback, resolve_account", "backend/tests/test_workspace_oauth.py",
      "OAuth/OIDC delegates identity verification to Google. Authlib checks state, S256 PKCE and signed ID-token claims; existing email accounts require authenticated linking.",
      "Run the mocked Google flow with real RSA/nonce validation. Wrong state, nonce, issuer, audience, expiry or signature redirects to a safe failure state; a valid fixture creates a viewer.", AUTH+"; GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and registered /api/v1/auth/google/callback",
      "State, PKCE, nonce and ID-token checks are tested with real RSA-signed fixtures; no live Google sign-in has been performed (needs the owner's OAuth client).", CREDENTIALS)
proof(7, "backend/app/auth/security.py", "password_hash, password_matches, revoke", SEC,
      "Argon2id is a memory-hard password hash with per-password salts; plaintext passwords are never stored. A password change invalidates existing sessions.",
      "Register, inspect the stored $argon2id$ prefix in a throwaway DB, verify correct/incorrect passwords, then change the password and demonstrate old JWT rejection.", AUTH)
proof(8, "backend/app/services/shared.py", "LIMIT_SCRIPT, limit, anonymous_id; AI RESERVE_SCRIPT", SEC+"; "+SERVICES,
      "Atomic shared counters enforce limits across processes; Redis TTL bounds each window. Authentication, password changes, imports, checkout, WebSocket connections and AI calls use shared controls.",
      "Run concurrent attempts: only the configured allowance succeeds, others get 429 with Retry-After. Disconnect Redis: protected work fails closed with 503.", "REDIS_URL; TEST_REDIS_URL must use dedicated DB 15; CLIENT_IP_HEADER=x-real-ip on Vercel only",
      REAL+" Exactly 7 of 40 concurrent attempts succeed. A spoofed X-Forwarded-For through the Compose Next.js proxy was shown to pass through unchanged, so CLIENT_IP_HEADER stays unset there.", FULL)
proof(9, "backend/app/auth/security.py", "current_user, require_roles", SEC+"; "+FLOW,
      "RBAC checks authoritative database roles at the backend. Viewer reads, researcher imports/reviews feedback, and admin manages account roles.",
      "Call an import route anonymously (401), as viewer (403), then as researcher (allowed). A researcher cannot list admin users; a signed fabricated role claim cannot grant access.", AUTH)
proof(10, "api/index.py", "app export; vercel.json rewrites", "backend/tests/test_r3_deployment.py; backend/tests/test_portable_model.py",
      "A serverless ASGI entry point serves FastAPI while packaging the immutable portable model and runtime dependencies.",
      "Inspect /api rewrites, run deployment configuration and minimal-runtime tests, then GET /api/v1/health locally: status ok. No new Vercel deployment was performed.", "Vercel project settings for deployment")
proof(11, "backend/app/api/endpoints/imports.py", "upload; parse_csv and write_rows in services/imports.py", FLOW+"; "+SERVICES+"; __tests__/workspace.test.tsx",
      "File handling bounds multipart input, validates every CSV row, and imports only research evaluation metadata inside one transaction.",
      "Sign in as researcher, create an import, submit the header template with approved metadata. Valid rows commit; unknown columns, invalid UTF-8, unsafe filenames and duplicate metrics fail without partial writes.", AUTH+"; existing model/cohort records", REAL+" End to end through the standalone Next.js proxy: upload 200, two rows committed.", FULL)
proof(12, "backend/app/main.py", "http_exception_handler; account/import/feedback endpoint responses", FLOW+"; backend/tests/test_stage6_security.py",
      "HTTP status codes communicate success, validation failure, missing identity, denied access, conflicts, rate limits and unavailable services consistently.",
      "Show 201 registration/import creation, 204 logout, 401 invalid JWT, 403 viewer import, 409 duplicate, 413 body cap, 422 invalid input, 429 quota and 503 unavailable integration.")
proof(13, "backend/app/api/middleware.py", "MonitoringMiddleware; WorkspaceBodyLimit", "tests/test_monitoring.py; "+FLOW,
      "Middleware wraps requests for cross-cutting behavior such as request IDs, monitoring and pre-parser body limits.",
      "Inspect middleware registration, request ID tests and the oversized auth request test. Bodies exceeding the cap are rejected before endpoint processing.")
proof(14, "backend/app/schemas/predict.py", "PredictRequest, PredictResponse; cardiovanta_ml.InferenceEngine", "backend/tests/test_stage3.py; backend/tests/test_r1_feature_contract.py",
      "Problem modeling expresses a fixed 13-feature research prediction contract with explicit outcome and threshold semantics.",
      "Submit a synthetic complete profile and inspect probability, feature directions and threshold_status. Missing inputs are rejected; the model artifacts are unchanged.")
proof(15, "backend/app/schemas/predict.py", "PredictRequest; Credentials, PasswordChange and Checkout models", "backend/tests/test_stage2.py; "+FLOW,
      "Request schemas enforce types, required fields, ranges and forbidden extras before business logic runs.",
      "Run missing/extra/binary/categorical feature tests and the upload column tests; invalid requests return sanitized 422 responses.")
proof(16, "backend/app/api/endpoints/accounts.py", "register, login, me; imports create_batch/batch_status/upload", FLOW+"; "+SEC,
      "REST endpoints represent resources and use HTTP methods for creation, retrieval, updates and deletion.",
      "Trace POST /research/imports to an ID, GET that ID, then POST its file. Compare the feedback POST/GET/PATCH/DELETE routes.")
proof(17, "backend/app/main.py", "validation_exception_handler, http_exception_handler; db.orm.session", "backend/tests/test_stage6_security.py; backend/tests/test_secrets_config.py; "+FLOW,
      "Server error handling maps failures to safe responses and rolls back incomplete work without exposing secrets or raw clinical input.",
      "Run provider/storage failure tests and sanitized validation logging tests. Verify no connection string or provider payload is returned.")
proof(18, "backend/app/main.py", "router composition; src/lib/workspace.ts workspaceRequest", "backend/tests/test_portable_model.py; __tests__/workspace.test.tsx",
      "System design separates browser interaction, API authorization, transactional metadata storage, optional shared infrastructure and immutable model inference.",
      "Follow one import from Workspace through JWT/RBAC to SQL, then its durable status to ImportLive. Explain why prediction serving still starts without database/provider secrets.", "See HLD.md and SETUP_AND_VERIFICATION.md for optional services")
proof(19, ".github/workflows/verify.yml", "verify-backend, quarantined-research-tests, verify-frontend", "backend/tests/test_r3_deployment.py; "+SEC+"; "+FLOW+"; "+SERVICES,
      "Automated API tests exercise contracts and failure cases; CI provisions real PostgreSQL, a Mongo replica set and Redis for integration tests.",
      "Run the classified safe pytest suite and Jest. Show local skips explicitly and the CI rules that fail rather than skip when service URLs are missing.", "Real-service suites verified locally (see 37-49); this branch's CI run happens when it is pushed")
proof(20, "docker-compose.yml", "frontend/backend/postgres/mongo/redis/migrate services", ".github/workflows/workspace-containers.yml",
      "Containers package reproducible application runtimes; Compose supplies health-checked dependencies and persistent local volumes. App processes run as non-root users.",
      "Run scripts/workspace_setup.py, docker compose --env-file .env.docker config --quiet, then up --build --wait. Verify both health endpoints and import WebSocket behavior.", "Docker Engine and Compose",
      "No Docker engine on the verification machine: images and Compose health checks have not been built or run. The same topology (standalone Next.js proxy, uvicorn, PostgreSQL, Mongo replica set, Redis) was verified end to end without containers.", DEPLOY)
proof(21, "backend/app/core/config.py", "Settings, SECRET_SETTINGS, require_secret", "backend/tests/test_secrets_config.py",
      "Environment configuration separates code from credentials; SecretStr masks values and integrations default to disabled.",
      "Run python -m backend.app.core.config: only presence is reported. Verify .env files are ignored and .env.example contains empty secret values.")
proof(22, "src/lib/api.ts", "prediction API helpers; workspaceRequest in src/lib/workspace.ts", "__tests__/encoding-and-coldstart.test.tsx; __tests__/workspace.test.tsx",
      "Async fetching lets the UI await remote results while displaying loading and error states.",
      "Submit a synthetic assessment or research import and inspect the network request plus pending, success and failure UI.")
proof(23, "src/components/shell/AppNav.tsx", "AppSidebar, MobileNav", "__tests__/navigation.test.tsx",
      "Client-side routing changes App Router pages through Next links while preserving the shared shell.",
      "Navigate Research → Workspace → Research or Heart Analysis; inspect active navigation and keyboard-accessible links.")
proof(24, "src/components/research/Workspace.tsx", "Workspace controlled email/password fields", "__tests__/workspace.test.tsx; __tests__/interactions.test.tsx",
      "Controlled inputs keep displayed form values synchronized with React state so validation and submission use the same data.",
      "Type an email and password; show onChange updating state and the exact submitted JSON in the component test.")
proof(25, "src/components/research/Workspace.tsx", "authenticate and import form", "__tests__/workspace.test.tsx; __tests__/contract.test.ts",
      "Client validation gives early feedback; backend schemas remain authoritative against bypassed browser controls.",
      "Create-account inputs require an email and at least 12 password characters; oversized CSV is rejected before import creation. Repeat invalid input directly against the API.")
proof(26, "next.config.ts", "standalone build and response headers", "backend/tests/test_r3_deployment.py; npm run build",
      "A production frontend build produces deployable server HTML, client bundles and static assets for Vercel or the container runtime.",
      "Run npm run build; show the static routes and the dynamic /research/evaluations route. The live Vercel deployment serves main; this branch was built locally, not deployed.", "Vercel project or Docker runtime for publication")
proof(27, "src/lib/workspace.ts", "workspaceRequest, refreshAccount", "__tests__/workspace.test.tsx; __tests__/async.test.ts",
      "async/await expresses nonblocking request sequencing with ordinary try/catch handling.",
      "Walk through awaiting batch creation, a scheduling turn and multipart upload; a rejection reaches the visible error message.")
proof(28, "src/components/research/ImportLive.tsx", "useEffect reconnect, polling and cleanup closures", "__tests__/import-live.test.tsx; __tests__/useEffectBehaviour.test.tsx",
      "Closures retain lexical state such as the current batch, reconnect delay and stopped flag across callbacks.",
      "Inspect reconnect and the cleanup callback; unmounting closes the captured socket and clears captured timers, proven by the test.")
proof(29, "src/lib/workspace.ts", "afterStatusUpdate", "__tests__/event-loop.test.ts",
      "JavaScript runs synchronous work first, Promise microtasks next, then timer tasks. The importer uses this boundary before starting its file request.",
      "Run the real-timer Node test: sync, caller, microtask, timer. React can flush its status update before the timer continuation; a timer turn alone does not guarantee a browser paint.")
proof(30, "src/lib/clinicalFormat.ts", "NO_ESTIMATE, describeEstimate", "__tests__/clinicalFormat.test.ts",
      "Function declarations are initialized before module execution; lexical bindings still have a temporal dead zone.",
      "Open NO_ESTIMATE calling describeEstimate before its declaration; run the declaration-vs-const hoisting tests and inspect fallback display text.")
proof(31, "src/lib/async.ts", "delay, withTimeout", "__tests__/async.test.ts",
      "Callbacks provide scheduled continuations; Promises model eventual completion and compose through race/await.",
      "Follow delay wrapping a timer callback in a Promise, then withTimeout racing the request and clearing its losing timer. Run success, timeout and abort tests.")
proof(32, "src/components/research/Workspace.tsx", "loading, busy, error and notice states", "__tests__/workspace.test.tsx; __tests__/encoding-and-coldstart.test.tsx",
      "Loading and error states explain what is happening and how to recover from unavailable services or failed requests.",
      "Show account initialization, disabled configuration, incorrect-password error, pending import and a retryable checkout error.")
proof(33, "src/components/shell/DocShell.tsx", "DocShell composing Workspace, Support and ImportLive", "__tests__/workspace.test.tsx; __tests__/page.test.tsx",
      "Component composition reuses the navigation/layout frame while isolating interactive account, import and support behavior.",
      "Open the server page wrapping Workspace in DocShell, then inspect ImportLive as a child receiving batch state and an update callback.")
proof(34, "src/app/workspace.css", "workspace-page, workspace-form, mobile media query", "__tests__/workspace.test.tsx; scripts/verify_workspace_ui.cjs; docs/viva/evidence/visual-check.json",
      "Responsive layout adapts spacing, wrapping and form controls to screen size while preserving keyboard focus and readable content.",
      "Inspect desktop 1440px and mobile 390px screenshots; verify no horizontal overflow and usable input labels. Authenticated screenshots use explicitly synthetic browser fixtures.")
proof(35, "src/components/research/ImportLive.tsx", "useEffect socket lifecycle", "__tests__/import-live.test.tsx; __tests__/useEffectBehaviour.test.tsx",
      "Effects synchronize component lifetimes with external subscriptions and clean up sockets/timers on dependency changes or unmount.",
      "Run the socket cleanup and polling tests; navigate away during an import and verify the connection and every timer are cleared.")
proof(36, "src/components/research/Workspace.tsx", "Workspace useState values", "__tests__/workspace.test.tsx; __tests__/interactions.test.tsx",
      "useState holds changing account, form and import state, triggering render updates through setters.",
      "Toggle sign-in/create-account, edit fields, select a file and display persisted import completion; each update comes from explicit state.")
proof(37, "backend/app/api/endpoints/feedback.py", "feedback_summary", "backend/tests/test_feedback_crud.py",
      "Mongo aggregation groups feedback by section and calculates total/helpful counts without transferring every document to Python.",
      "Create synthetic helpful/unhelpful feedback and GET /feedback/summary; inspect $group, $sum, $cond and $sort.", MONGO, REAL, FULL)
proof(38, "backend/app/api/endpoints/feedback.py", "create_feedback, read_feedback, update_feedback, delete_feedback", "backend/tests/test_feedback_crud.py; "+SERVICES,
      "Mongo CRUD persists anonymous votes and allows their owner to update or withdraw them using a one-time returned edit credential.",
      "Create (201), read (200), update with X-Edit-Token (200), delete (204), then read (404). Incorrect tokens cannot modify the record.", MONGO, REAL, FULL)
proof(39, "backend/app/db/mongo_setup.py", "FEEDBACK_SCHEMA.metadata, EVENTS; feedback transaction writes", SERVICES,
      "Small bounded metadata is embedded for frequent reads; potentially growing audit events reference the parent ObjectId in another collection.",
      "Inspect metadata embedded in a feedback document and two referenced create/update events. Delete the parent: a Mongo transaction deletes its events too.", MONGO, REAL, FULL)
proof(40, "backend/app/db/mongo_setup.py", "setup; research_feedback and research_feedback_events", SERVICES,
      "Compound Mongo indexes support equality filters followed by creation-date ordering, and parent-filtered event history.",
      "Inspect section/date, model-version/date and parent/date indexes; run the explain-plan test. Without any hint, MongoDB's planner chooses the section/date IXSCAN and needs no SORT stage.", MONGO, REAL, FULL)
proof(41, "backend/app/db/mongo_setup.py", "FEEDBACK_SCHEMA, EVENT_SCHEMA, setup", SERVICES,
      "Database-level JSON Schema enforces types and allowed fields even when a writer bypasses FastAPI. The migration backfills safe metadata and refuses existing invalid documents.",
      "Run setup twice; insert an invalid section or clinical_input directly with PyMongo and observe WriteError. Valid feedback remains accepted.", MONGO, REAL, FULL)
proof(42, "backend/app/db/research.py", "VERSION_COVERAGE_SQL, UNEVALUATED_COHORTS_SQL", SQL,
      "SQL filtering, ordering and grouping turn research records into stable evaluation tables, coverage counts and missing-evaluation lists.",
      "Run the three queries after migrations; explain WHERE IS NULL, ORDER BY and GROUP BY. Model versions without evaluations remain visible.", PG, REAL, FULL)
proof(43, "backend/app/db/sql/001_research_schema.sql", "evaluations_model_version_idx, evaluations_cohort_idx; migration 003 session indexes", SQL+"; "+SERVICES,
      "Indexes accelerate actual join/filter and cleanup access paths while uniqueness indexes prevent duplicate identities and metrics.",
      "Run test_real_postgres_planner_uses_the_declared_indexes: with 20,000 synthetic sessions and batches, PostgreSQL's planner chooses refresh_sessions_expiry_idx for clean-up and upload_batches_owner_idx (no Sort node) for a user's recent imports.", PG, REAL, FULL)
proof(44, "backend/app/db/sql/003_accounts_operations.sql", "users, roles, user_roles, oauth_accounts, refresh_sessions", SQL+"; "+SERVICES,
      "Normalization separates users, roles, identities and sessions so repeated facts are not copied into unrelated rows.",
      "Trace a user through its role and OAuth mapping, and an evaluation through model/cohort/metrics. Explain why a role change does not rewrite every session.", PG, REAL, FULL)
proof(45, "backend/app/db/orm.py", "User, Role, RefreshSession, UploadBatch, SupportPayment, session", SEC+"; "+SERVICES,
      "SQLAlchemy 2 maps Python entities to SQL rows and coordinates identity, relationships and explicit transactions. It is the Python-stack equivalent of the rubric's Prisma/Sequelize examples.",
      "Open registration adding User with Role relationships and session rotation adding RefreshSession. Compare ORM operations with the retained raw research JOIN queries.", PG, REAL+" Registration, role change, import and refresh rotation ran through the ORM on PostgreSQL.", FULL)
proof(46, "backend/app/db/sql/003_accounts_operations.sql", "PRIMARY KEY, REFERENCES, UNIQUE, ON DELETE constraints", SQL+"; "+SERVICES,
      "Relational keys give rows stable identity, connect related entities and prevent orphaned or duplicate records.",
      "Run migration/FK tests and attempt an orphan metric or role mapping in a transaction: PostgreSQL rejects it.", PG, REAL, FULL)
proof(47, "backend/app/db/research.py", "EVALUATION_TABLE_SQL, VERSION_COVERAGE_SQL, UNEVALUATED_COHORTS_SQL", SQL,
      "INNER JOIN returns complete metric provenance; LEFT JOIN preserves models with no evaluations; an anti-join identifies unevaluated cohorts.",
      "Run each query and point out the seeded zero-evaluation model and unevaluated cohorts. Compare why INNER JOIN would hide those gaps.", PG, REAL, FULL)
proof(48, "backend/app/db/migrate.py", "apply_migrations; imports.upload and services.imports.write_rows", SQL+"; "+SERVICES,
      "Transactions make migrations and multi-row imports atomic: either all intended writes commit or none survive.",
      "Run migrations twice, then import a file whose second metric duplicates an existing one. The first new metric must also roll back.", PG, REAL, FULL)
proof(49, "backend/app/services/shared.py", "cache_read, cache_write, invalidate_research", SEC+"; "+SERVICES,
      "Read-through Redis caching avoids repeated public research SQL queries; TTL bounds staleness and successful imports invalidate the cache. No individual predictions are cached.",
      "GET research evaluations twice (MISS then HIT), import a metric (invalidation), and test expiration. Redis outage falls back to SQL for public reads, while security limits fail closed.", "REDIS_URL, RESEARCH_CACHE_TTL; DATABASE_URL", REAL+" End to end: MISS, HIT, import, MISS with the new rows visible.", FULL)
proof(50, "backend/app/api/endpoints/payments.py", "checkout, webhook, record_event", FLOW,
      "Stripe Checkout handles payment details externally. Only signed test-mode webhook events can mark a support record paid; duplicate event IDs are idempotent.",
      "Run synthetic signed-webhook tests, invalid signatures, repeated delivery and provider failure. With owner test credentials, complete Checkout and verify the Stripe event and PostgreSQL paid record.", "PAYMENTS_ENABLED=true, sk_test_ STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, DATABASE_URL, REDIS_URL", "Mocked Stripe/signature tests pass; no real Stripe test event was processed and no payment is claimed.", CREDENTIALS)
proof(51, "backend/app/api/endpoints/maintenance.py", "authorize, maintain, daily; vercel.json crons", FLOW+"; "+SERVICES,
      "A protected daily cron removes expired authentication state, marks abandoned import attempts failed and records one idempotent maintenance result per UTC date.",
      "Call without the cron bearer secret (401), call with it (completed), and repeat (already_completed). Inspect retained research/feedback and removed expired sessions.", "CRON_SECRET of at least 32 characters, DATABASE_URL; Vercel production cron at 03:00 UTC / 08:30 Asia/Kolkata", "PostgreSQL advisory-lock integration verified: six overlapping invocations on real PostgreSQL produce exactly one run. A scheduled invocation by Vercel has not been observed (requires a deployment with CRON_SECRET).", DEPLOY)
proof(52, "src/app/research/evaluations/page.tsx", "ResearchEvaluationsPage (dynamic = force-dynamic); lib/serverResearch.ts loadEvaluationsOnServer; EvaluationsTable", "__tests__/ssr-evaluations.test.tsx; npm run build",
      "Server-side rendering produces HTML on the server for each request. /research/evaluations reads the live research database through the API (cache: no-store) and sends a finished table, so it works without JavaScript and shows an import immediately. /research, by contrast, is prerendered once at build time (SSG) and fetches the same table in the browser.",
      "npm run build marks /research/evaluations as dynamic and writes no HTML for it. Start the server with RESEARCH_API_ORIGIN, then curl the page twice: two different server timestamps and the database rows in the raw HTML (verified 2026-11-28, including rows imported moments earlier).",
      "RESEARCH_API_ORIGIN (server-only) naming the API origin reachable from the Next.js server")
proof(53, "backend/app/api/endpoints/realtime.py", "live, snapshot; src/components/research/ImportLive.tsx (socket + polling fallback)", FLOW+"; __tests__/import-live.test.tsx; scripts/verify_workspace_deployment.py",
      "An authenticated WebSocket sends durable import states and heartbeats. Reconnects re-read PostgreSQL, so another serverless instance can resume without an in-memory job registry.",
      "Create a batch, connect, send the JWT as the first message and upload metadata. Observe ready then completed; a wrong Origin is refused at the handshake and a bad token is closed 1008. Where sockets are unavailable the page falls back to authenticated polling after three failed connections.",
      AUTH+"; REALTIME_ENABLED=true on a host that can hold WebSocket connections (Docker/uvicorn)",
      "Verified 2026-11-28 through the production-shaped stack (standalone Next.js proxy, uvicorn, real PostgreSQL/Redis). Vercel Functions do not host WebSocket servers, so production on Vercel relies on the polling fallback, which is unit-tested but has not been observed on a deployment.", DEPLOY)


def link(path):
    if (ROOT / path).is_file():
        return f"[{path}](../../{path})"
    return f"`{path}`"


def main():
    assert len(records) == len(evidence) == 53
    intro = """# 53-concept implementation matrix

Recorded 2026-11-28, branch `feature/complete-53-viva-concepts`, based on fetched `origin/main` e6b7250.
Statuses (see CONTINUATION_REPORT.md for the audit behind them):

* **FULL**: fully implemented and tested. Database, cache and rate-limit behaviour was tested against real services
  (PostgreSQL 16.6, MongoDB 7.0.14 replica set, Redis 5.0.14), not mocks.
* **DEPLOY_PENDING**: implemented and tested; verification in the target deployment is still outstanding.
* **NEEDS_CREDENTIALS**: implemented and tested with mocked providers; a live demonstration needs the owner's
  credentials (Google, OpenAI, Stripe test keys). No live provider call or payment is claimed.
* **PARTIAL** / **NOT_IMPLEMENTED**: none at present.

FULL does not mean this branch is deployed.

| # | Exact concept | Rubric category | Points | Initial | Final | Source / symbol | Test evidence | Demonstration / final proof | External configuration / outstanding |
|---:|---|---|---:|---|---|---|---|---|---|
"""
    rows, guide = [], ["# Viva demonstration guide\n\nUse synthetic inputs and metadata only. Start with [setup and verification](SETUP_AND_VERIFICATION.md).\nRead the status on each concept before claiming completion. Mocked tests are not live provider/deployment proof.\n"]
    for record in records:
        n = record["number"]; item = evidence[n]
        assert (ROOT / item["source"]).exists(), item["source"]
        for test in item["tests"].split("; "):
            if test.endswith((".py", ".tsx", ".ts", ".yml")):
                assert (ROOT / test).exists(), test
        record.update(item)
        refs = "; ".join(link(p) for p in item["tests"].split("; "))
        pending = item["pending"] or "Local implementation proof passed; no new deployment claimed."
        rows.append(f"| {n} | {record['concept']} | {record['category']} | {record['points']} | {record['initial']} | {item['final']} | {link(item['source'])}: {item['symbol']} | {refs} | {item['demo']} | {item['configuration']}. {pending} |")
        guide.append(f"## {n}. {record['concept']}\n\n**{record['category']} · {record['points']} points · {LABELS[item['final']]}**\n\n"
                     f"**Meaning and purpose:** {item['meaning']}\n\n**Open:** {link(item['source'])} — `{item['symbol']}`.\n\n"
                     f"**Demonstration and expected behavior:** {item['demo']}\n\n**Automated evidence:** {refs}.\n\n"
                     f"**Viva explanation:** “{item['meaning']}”\n\n**Configuration:** {item['configuration']}.\n\n**Verification limit:** {pending}\n")
    (DEST / "53-concept-implementation-matrix.md").write_text(intro+'\n'.join(rows)+'\n', encoding="utf-8")
    (DEST / "VIVA_DEMONSTRATION_GUIDE.md").write_text('\n'.join(guide), encoding="utf-8")
    (DEST / "concepts.json").write_text(json.dumps(records, indent=2, ensure_ascii=False)+'\n', encoding="utf-8")
    totals = Counter(r['final'] for r in records)
    summary = " · ".join(f"{LABELS[k]}: {totals.get(k, 0)}" for k in (FULL, DEPLOY, CREDENTIALS, PARTIAL, MISSING))
    matrix = DEST / "53-concept-implementation-matrix.md"
    matrix.write_text(matrix.read_text(encoding="utf-8").replace("Statuses (see", f"**{summary}**\n\nStatuses (see", 1), encoding="utf-8")
    categories = {}
    for row in records:
        categories.setdefault(row['category'], Counter())['total'] += 1
        categories[row['category']][row['final']] += 1
    (DEST / "scorecard.json").write_text(json.dumps(dict(totals=dict(totals), labels=LABELS, categories=categories), indent=2)+'\n', encoding="utf-8")
    print(dict(totals))


if __name__ == "__main__":
    main()
