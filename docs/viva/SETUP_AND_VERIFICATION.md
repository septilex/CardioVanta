# Setup and verification

How to reproduce every result in the [53-concept matrix](53-concept-implementation-matrix.md). All data used here is
synthetic research metadata; no patient or clinical data is involved. Every optional integration is disabled until
its configuration is present, and prediction serving starts without any of it.

## 1. Tests that need no services

```bash
python -m pytest                      # backend + research; real-service tests skip locally, never in CI
npx jest                              # frontend
npm run build                         # production build; /research/evaluations is the only dynamic page
```

## 2. Real-service integration tests

The integration tests run against **real** PostgreSQL, a MongoDB **replica set** (feedback writes use multi-document
transactions) and Redis. CI starts them as service containers. Locally, use Docker Compose or portable binaries:

```bash
# PostgreSQL 16 on 55432, MongoDB 7 as replica set rs0 on 57017, Redis on 56379 (any reachable instances work)
initdb -D pgdata -U postgres --auth=trust && pg_ctl -D pgdata -o "-p 55432 -c listen_addresses=127.0.0.1" start
psql -h 127.0.0.1 -p 55432 -U postgres -c "CREATE DATABASE cardiovanta_test"
mongod --replSet rs0 --port 57017 --bind_ip 127.0.0.1 --dbpath mongodata
#   then once: db.adminCommand({replSetInitiate: {_id: "rs0", members: [{_id: 0, host: "127.0.0.1:57017"}]}})
redis-server --port 56379 --bind 127.0.0.1

export TEST_DATABASE_URL=postgresql://postgres@127.0.0.1:55432/cardiovanta_test
export TEST_MONGODB_URI="mongodb://127.0.0.1:57017/cardiovanta_test?replicaSet=rs0"
export TEST_REDIS_URL=redis://127.0.0.1:56379/15     # database 15 is required; tests clear cv:* keys there
python -m pytest -rs                                  # only CI-only checks skip
```

The tests refuse to run against anything but localhost or a database whose name ends in `_test`.

## 3. Production-shaped stack (the Docker topology without containers)

```bash
# backend: real services, accounts and live status enabled (synthetic secrets generated locally)
export DATABASE_URL=postgresql://postgres@127.0.0.1:55432/cardiovanta_e2e MONGODB_URI=... REDIS_URL=redis://127.0.0.1:56379/3
export AUTH_ENABLED=true JWT_SIGNING_KEY=<48 random bytes> APP_ORIGIN=http://localhost:3100 COOKIE_SECURE=false
export ENVIRONMENT=development REALTIME_ENABLED=true CORS_ORIGINS='["http://localhost:3100"]'
python -m backend.app.db.setup                        # PostgreSQL migrations 001-003, Mongo validators and indexes
uvicorn backend.app.main:app --host 127.0.0.1 --port 8100 --no-proxy-headers

# frontend: standalone server proxying /api to the backend, with server-side rendering enabled
API_PROXY_TARGET=http://127.0.0.1:8100 npm run build
cp -r .next/static .next/standalone/.next/static && cp -r public .next/standalone/public
RESEARCH_API_ORIGIN=http://127.0.0.1:8100 PORT=3100 node .next/standalone/server.js
```

Register an account through `http://localhost:3100/api/v1/auth/register`, grant a role with the operator tool
`python -m backend.app.auth.bootstrap <email>` (there is no HTTP route for this), then:

```bash
VIVA_BASE_URL=http://localhost:3100 VIVA_EMAIL=... VIVA_PASSWORD=... python scripts/verify_workspace_deployment.py
curl -s http://localhost:3100/research/evaluations | grep -o 'dateTime="[^"]*"'   # differs on every request
```

With Docker available the same stack is `python scripts/workspace_setup.py` then
`docker compose --env-file .env.docker up --build --wait`.

## 4. Proxy client identity

Anonymous rate limits key on the client address. Set `CLIENT_IP_HEADER=x-real-ip` **only** where the edge overwrites
that header (Vercel). Leave it unset behind the Compose Next.js proxy: it forwards a client-supplied
`X-Forwarded-For` unchanged, which was demonstrated on 2026-11-28 (a spoofed value created its own rate-limit bucket).

## 5. What needs the owner

| Concept | Needed for a live demonstration |
|---|---|
| 1 LLM API | `LLM_ENABLED=true`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `AI_SIGNING_KEY`, `REDIS_URL` |
| 6 Google sign-in | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, redirect URI `<APP_ORIGIN>/api/v1/auth/google/callback` |
| 20 Docker | a Docker Engine (or the `Workspace container verification` workflow on a pull request) |
| 50 Stripe | `PAYMENTS_ENABLED=true`, an `sk_test_` key, `STRIPE_WEBHOOK_SECRET`; only test mode is accepted |
| 51 Cron on Vercel | `CRON_SECRET` (≥ 32 characters) and a deployment; Vercel calls `/api/v1/maintenance/daily` at 03:00 UTC |
| 53 Live status on Vercel | deploy and confirm the polling fallback; Vercel Functions do not host WebSocket servers |
