# Continuation report — takeover from Codex Astra

Recorded 2026-11-28 in `C:\AntiGravity Projects\CardioVanta-53-concepts`, branch
`feature/complete-53-viva-concepts`. The original `C:\AntiGravity Projects\CardioVanta` working directory was not
modified.

## 1. State found (forensic audit)

| Item | Finding |
|---|---|
| Branch | `feature/complete-53-viva-concepts`, based on `origin/main` `e6b7250` (PR #7). The local `main` ref is stale (`446788d`); all comparisons below use `origin/main`. |
| Committed by Astra | `332ce38` accounts/JWT/OIDC/roles/Redis and `12b8c1d` imports/feedback history/operational services — 40 files, +2,392 / −18. |
| Uncommitted (modified) | `.env.example`, `.github/workflows/verify.yml` (Redis service, MongoDB replica set), `.gitignore`, `docs/viva/53-concept-implementation-matrix.md`, `docs/viva/concepts.json`, `jest.config.ts`, `next.config.ts` (standalone output, API proxy rewrite), `src/app/research/page.tsx`, `next-env.d.ts` (dev-server generated; not to be committed). |
| Untracked | 28 files: Docker (`Dockerfile`, `docker-compose.yml`, `.dockerignore`, `workspace-containers.yml`), workspace/support UI, `src/lib/workspace.ts`, three Jest suites, viva generator and evidence screenshots, setup/verification scripts, CSV template. |
| Preservation | Before any change, the uncommitted patch (`git diff --binary`) and copies of all 28 untracked files were saved outside the repository. Nothing was reset, stashed, cleaned or overwritten. |
| `git diff --check` | Clean. |
| Python environment | `.venv` contains `cardiovanta-existing.pth`, which adds the **original** project's `site-packages` to `sys.path` (read-only). Project code (`backend`, `cardiovanta_ml`) is imported from this directory, but some third-party packages resolve from the original venv, so final validation uses a clean environment built only from the pinned requirements. |

## 2. Reported vs verified

| Astra's report | Verified finding |
|---|---|
| Argon2id, short-lived JWT, hashed refresh rotation | Correct. HS256 only; `iss`/`aud`/`exp`/`nbf`/`iat`/`jti`/`ver` required; lifetime ≤ 15 min; refresh rows locked `FOR UPDATE`; reuse revokes every session; constant-shape login with a dummy hash; rehash on login. |
| Backend RBAC | Every account/role/import/research-feedback route depends on `current_user` or `require_roles` (route inventory generated from the running app). Remaining open routes are public by design (status, register/login/refresh, public research, gated `/predict`, token-guarded anonymous feedback, signature-verified webhook, secret-guarded cron). |
| Google OAuth (state, PKCE, nonce, iss/aud/exp) | Correct. Server-side one-use flow consumed with `DELETE … RETURNING` before token exchange; no silent linking to existing password accounts. Only mocked provider tests exist. |
| Shared Redis quotas / caching | Atomic Lua `INCR`+`EXPIRE`; fail-closed limits, fail-open cache. **Defect:** the client identity is the socket peer address, which behind Vercel or the Compose Next.js proxy is the proxy, so all anonymous users share one bucket. |
| Bounded CSV imports | Correct: 256 KiB streaming body limit, strict filename/content type, exact header, ≤ 500 rows, whitelisted values, one transaction, no clinical columns. |
| Stripe Checkout + signed webhook | Correct for test mode: signature with 300 s tolerance, idempotent event table, amount/currency/reference cross-check, live events rejected. No real Stripe event processed. |
| Cron endpoint | Correct: constant-time bearer check, ≥ 32-char secret, advisory lock, once-per-day record. Vercel invocation unverified. |
| WebSocket endpoint | Correct authorization (exact Origin, token as first message, re-verified each poll). **Gap:** Vercel serverless functions cannot host WebSocket servers, and the UI retries forever without a polling fallback. |
| Docker | Non-root images, health checks, replica-set init, research data excluded. Never built (no Docker engine locally). |
| Dependency security pins | `pip-audit` on all three Python requirement files and `npm audit` (runtime and dev): **no known vulnerabilities** (re-run 2026-11-28). |
| Baseline tests | Reproduced exactly: backend **668 passed, 19 skipped**; frontend **147/147** (18 suites). All 19 skips are real-service tests (PostgreSQL, MongoDB, Redis) or CI-only checks. |
| 33 FULL / 20 PARTIAL | Not accepted as stated. #52 (SSR) cites a non-existent evidence file and the cited page is statically prerendered (SSG), not request-time SSR. The guide links a missing `SETUP_AND_VERIFICATION.md`. |

## 3. Classification at takeover

* **Finished and sound:** auth core (5, 7, 9), OAuth logic (6), CSV validation (11), Stripe logic (50), cron logic (51), body limits, RBAC, AI layer (2, 3), frontend concepts 22–36.
* **Partially finished:** rate limiting (client identity behind proxies), WebSocket (no production fallback), SSR (no request-time rendering evidence), viva docs (two-state taxonomy, missing file, stale text).
* **Validation pending:** every PostgreSQL, MongoDB and Redis integration test (never run against real services), Docker builds and Compose health, clean-environment dependency install.
* **Mocked only:** Google OIDC, OpenAI, Stripe.
* **Requires external credentials:** Google OAuth client, OpenAI API key, Stripe test keys and webhook secret, production Redis/PostgreSQL/MongoDB, Vercel `CRON_SECRET`.
* **Untested in the target environment:** Vercel cron invocation, Vercel WebSocket behaviour, Docker Compose stack.

## 4. Continuation plan

1. Run every skipped integration test against real disposable PostgreSQL 16, MongoDB 7 (single-node replica set) and Redis services.
2. Fix the proxy client-identity defect with an explicit, opt-in trusted header.
3. Add an HTTP polling fallback to live import status so production degrades gracefully without WebSockets.
4. Add genuine request-time server-side rendering evidence for #52.
5. Extend the viva generator to the five-status taxonomy, add the missing setup guide, correct stale text.
6. Validate in a clean environment (pinned requirements only), build, audit, and record exact results.

## 5. Outcome of the continuation (2026-11-28)

| Item | Result |
|---|---|
| Real-service validation | All 19 previously skipped tests now run against real PostgreSQL 16.6, MongoDB 7.0.14 (replica set `rs0`) and Redis 5.0.14 and pass; only CI-only assertions and the optional wheel-install test skip. Repeated runs on a reused database pass. |
| Hidden regressions found by real services | `test_endpoint_returns_the_join_results` still expected `public, max-age=300` after the move to Redis caching; the research fixture left migration-003 tables behind, failing the second run. Both fixed (tests updated to the intended contract). |
| Index and lock proof | New tests: PostgreSQL's planner chooses `refresh_sessions_expiry_idx` and `upload_batches_owner_idx` (no sort) at 20,000 rows; six overlapping cron calls run the day's maintenance exactly once; MongoDB chooses the feedback index without the previously forced `hint`. |
| Client identity | Opt-in `CLIENT_IP_HEADER`. End-to-end testing showed the Compose Next.js rewrite forwards a client-supplied `X-Forwarded-For` unchanged, so the setting is **not** used there (an initial Compose setting of it was caught by that test and removed before commit); `x-real-ip` is documented for Vercel only. |
| WebSocket | Verified through a production build of the standalone Next.js proxy, uvicorn and real services: authenticated upgrade, `ready` → `completed`, wrong Origin refused (403), bad token closed 1008. Polling fallback added for hosts without WebSockets (Vercel). |
| Server-side rendering | New `/research/evaluations` (force-dynamic). Verified with `curl` on a production server: distinct server timestamps per request and live database rows, including rows imported moments earlier, in the raw HTML. |
| Lint | Two `react-hooks/set-state-in-effect` errors in the workspace/support components resolved by deriving URL messages with `useSyncExternalStore`. |
| Docker | Still not built: no Docker engine on the machine, and downloading a standalone Compose binary was declined by the session's permission policy. Recorded as deployment verification pending. |
| Commits (local, not pushed) | `b099c2e` (Astra's uncommitted work, byte for byte from the takeover snapshot), `598360c`, `fb06cce`, `21a29c5`, `36c53cb`, `ea91db5`, and the documentation commit. |

Unreproduced observation: one run of the real-Redis rate-limit test returned 503 (limiter fail-closed on a Redis error)
instead of 429. Eleven subsequent full runs and a 400-call, 16-thread stress burst produced no error. Recorded, not
explained.
