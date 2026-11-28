# Implementation report

Branch `feature/complete-53-viva-concepts` in `C:\AntiGravity Projects\CardioVanta-53-concepts`, based on
`origin/main` `e6b7250`. The original `CardioVanta` working directory was not modified. Nothing on this branch has
been deployed; it is open as PR #9 (not merged).

## Current status — 2026-11-28

| Status | Count | Concepts |
|---|---:|---|
| Fully implemented and tested | **48** | all except those below |
| Implemented; deployment verification pending | **2** | 51 Cron (Vercel invocation), 53 WebSocket (Vercel fallback) |
| Implemented; requires external credentials for live proof | **3** | 1 LLM (OpenAI key), 6 Google OAuth (client), 50 Stripe (test keys) |
| Partially implemented | 0 | |
| Not implemented | 0 | |

All 53 concepts have code, automated tests and a reproducible demonstration in the
[demonstration guide](VIVA_DEMONSTRATION_GUIDE.md); per-concept evidence is in the
[matrix](53-concept-implementation-matrix.md). "Fully implemented and tested" means database, cache and rate-limit
behaviour ran against real services, not mocks. It does not mean this branch is deployed.

## History

| Stage | Result |
|---|---|
| Supplied baseline | 36 full, 5 partial, 12 missing (initial audit, not a certification). Frontend 136 tests; backend 629 passed, 15 skipped. |
| Codex Astra | Accounts (Argon2id, JWT, refresh rotation, RBAC), Google OIDC, Redis limits and caching, CSV imports, Stripe test checkout, cron, WebSocket status, Docker, workspace/support UI, viva generator. Self-assessed 33 FULL / 20 PARTIAL. Left 36 files uncommitted; dependency audit unfinished. |
| Takeover audit | See [CONTINUATION_REPORT.md](CONTINUATION_REPORT.md). Baseline reproduced exactly (668 passed, 19 skipped; frontend 147). Two FULL claims did not hold (#52 SSR was SSG with a missing evidence file; #6 had no live provider proof). |
| Continuation | Real-service validation, client-identity fix, WebSocket polling fallback, request-time SSR page, lint fixes, five-status viva generator, setup guide. |

## Validation results (2026-11-28)

| Check | Command | Result |
|---|---|---|
| Backend + research, real services | `pytest` with `TEST_DATABASE_URL`, `TEST_MONGODB_URI` (replica set), `TEST_REDIS_URL` | **693 passed, 4 skipped** (3 CI-only assertions, 1 optional wheel install) |
| Frontend | `npx jest` | **162 passed** (19 suites) |
| Types | `npx tsc --noEmit` | clean |
| Lint (changed areas) | `npx eslint src/components/research src/lib src/app/research …` | clean |
| Production build | `npm run build` | passes; `/research/evaluations` dynamic, all other pages static |
| Dependency audit | `pip-audit -r` backend, api, test requirements; `npm audit` | no known vulnerabilities |
| Secret scan | patterns for provider keys, private keys and credentialed URLs over every changed file | none (one documented placeholder) |
| End to end | standalone Next.js proxy + uvicorn + real PostgreSQL/MongoDB/Redis; `scripts/verify_workspace_deployment.py` and a lifecycle script | login/RBAC, import, WebSocket `ready → completed`, cache MISS/HIT/invalidation, Origin and token rejection, SSR per request |
| CI on PR #9 (`207811c`) | GitHub Actions runs 46130345315 and 46130345355 | backend 838 passed / 2 skipped; research stack 842 passed / 3 skipped (pre-existing platform skips; every real-service test ran); frontend 19 suites; audits clean; **Docker: three images built, full Compose stack healthy, smoke checks passed** |
| Clean environment | fresh virtualenv from the pinned requirements only (no link to any other environment), real services, `CARDIOVANTA_RUN_INSTALL_TESTS=1` | **694 passed, 3 skipped** (CI-only assertions); `pip-audit` of the installed environment: no known vulnerabilities |

## Defects found and fixed during continuation

1. **Shared anonymous rate-limit bucket behind proxies** — every client keyed on the proxy address. Added the opt-in,
   allowlisted `CLIENT_IP_HEADER`. End-to-end testing then showed the Compose Next.js rewrite forwards a
   client-supplied `X-Forwarded-For` unchanged, so it must not be trusted there; a guard test enforces that.
2. **Stale integration test** — expected `Cache-Control: public, max-age=300` after the move to Redis caching
   (`no-store` is correct: imports invalidate the cache immediately).
3. **Non-reentrant test fixture** — migration-003 tables survived between runs on a reused test database.
4. **Live import status on Vercel** — retried WebSockets forever; now falls back to authenticated polling.
5. **SSR evidence** — every page was prerendered; added a genuine request-time page and its tests.
6. **Index proof** — the Mongo test forced the index with `hint`; replaced by the planner's own choice, and added a
   PostgreSQL `EXPLAIN` test at realistic volume.
7. **Cron concurrency** — advisory lock proven with six overlapping calls on real PostgreSQL.
8. **Lint** — two `set-state-in-effect` errors.

## Files changed in the continuation

Backend: `backend/app/core/config.py`, `backend/app/services/shared.py`.
Backend tests: `backend/tests/test_workspace_security.py`, `backend/tests/test_workspace_services.py`,
`backend/tests/test_research_db.py`.
Frontend: `src/components/research/ImportLive.tsx`, `EvaluationsTable.tsx` (new), `DatabaseEvaluations.tsx`,
`Support.tsx`, `Workspace.tsx`, `src/lib/serverResearch.ts` (new), `src/lib/useQueryParam.ts` (new),
`src/app/research/evaluations/page.tsx` (new), `src/app/research/page.tsx`.
Frontend tests: `__tests__/import-live.test.tsx`, `__tests__/ssr-evaluations.test.tsx` (new),
`__tests__/workspace.test.tsx`.
Configuration: `.env.example`, `docker-compose.yml`.
Documentation: `scripts/build_viva_docs.py` and its generated `53-concept-implementation-matrix.md`,
`VIVA_DEMONSTRATION_GUIDE.md`, `concepts.json`, `scorecard.json`; `CONTINUATION_REPORT.md`,
`SETUP_AND_VERIFICATION.md` and this report (new or rewritten).

No model artifacts, model versions, feature contracts, thresholds or prediction semantics were changed, and
`configs/prediction_service.json` is untouched (predictions remain disabled).

## Remaining requirements

* **Deployment (#51, #53):** after deployment, confirm a scheduled Vercel cron call (`CRON_SECRET` set) and the
  live-status polling fallback on Vercel. Set `CLIENT_IP_HEADER=x-real-ip` and, optionally, `RESEARCH_API_ORIGIN`.
* **Credentials (#1, #6, #50):** OpenAI key, Google OAuth client, Stripe test keys and webhook secret.
* **Production services:** PostgreSQL, a MongoDB replica set (feedback uses multi-document transactions) and Redis.

## Known limitations

* Real-service tests ran against Redis 5.0.14 (a Windows build), not the Redis 7 used in CI and Compose. The Lua
  limiter uses only commands available in both.
* One unexplained 503 in a single run of the Redis rate-limit test (see the continuation report).
* The 2-row end-to-end import completes within one status poll, so the intermediate `validating`/`importing` states
  were not observed over the socket (they are covered by unit tests).
* Vercel's handling of `x-real-ip` and WebSocket upgrades is documented behaviour, not observed on a deployment of
  this branch.
