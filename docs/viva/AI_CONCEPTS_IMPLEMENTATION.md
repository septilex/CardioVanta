# Implemented AI explanation layer

## LLM API integration
backend/app/ai/client.py: provider_parse initializes official AsyncOpenAI lazily,
uses chat.completions.parse, a 20-second SDK timeout and 25-second overall deadline,
max_retries=0, store=False and an explicit OpenAI destination. explain handles errors
without logging provider payloads. No model inference is called by this service.
backend/app/api/endpoints/ai_explanation.py: explanation implements POST /api/v1/ai/explanation;
status implements GET /api/v1/ai/status. Disabled/missing configuration returns 503.
Rate limits return 429, timeouts 504, unavailable provider 503, invalid output 502.

## Prompt engineering
backend/app/ai/prompts/explanation_v1.py: SYSTEM and VERSION are version-controlled.
A fixed system role separates instructions from consistently serialized JSON data.
No free-form user instructions, tools, clinical records or identifiers are accepted.
Feature names and contribution directions are allowlisted. Inputs are bounded to 8 KiB,
13 unique factors and a finite probability in [0,1]. Unknown fields are rejected.
The prompt distinguishes model association from causation, prohibits diagnosis,
treatment and invented scores, and explains uncertainty. These instructions reduce
risk but cannot guarantee factual or medical correctness of generated prose.

## Structured outputs
backend/app/ai/schemas.py: ExplanationContent is passed as response_format to the
SDK typed parsing method. It defines required, bounded fields and forbids extras.
explain rejects refusal, incomplete output, absent parsed output, schema violations
and changed feature names/directions. ExplanationResponse adds the fixed disclaimer,
next step and server-controlled prompt version. JSON validation alone cannot establish
clinical accuracy. No generated data is written into the original prediction object.

## UI and privacy
src/lib/aiExplanation.ts: minimizeResult sends only the signed explanation token to
the backend. The token contains probability, outcome and feature directions from the
existing uncalibrated explanation; it does not contain contribution magnitudes, raw
input values, identifiers or metadata. The backend forwards only the token's validated
derived data to OpenAI. These data and the bearer token are still sensitive.
src/app/assessment/AIExplanation.tsx checks availability and requires a button click
after disclosure. It supports loading, errors and retry, retaining the original result.
Successful results remain in component memory; no new database storage is introduced.

## Configuration and demonstration
Install backend/requirements.txt in the project virtual environment. Both dependency
manifests pin openai==2.8.1. Configure backend-only OPENAI_API_KEY, OPENAI_MODEL (a
model supporting structured outputs), and LLM_ENABLED=true only after privacy review,
provider retention review and appropriate access/budget controls. Default LLM_ENABLED=false.
Never use NEXT_PUBLIC for secrets. AI is forcibly unavailable when VERCEL is set; do not
enable it in Vercel until shared durable quota storage and privacy review are complete.
Locally run uvicorn backend.app.main:app --reload and npm run dev. Existing API base
URL conventions apply. Obtain a normal result, then activate the optional explanation.

Example POST body:
```json
{"probability":0.4,"outcome":"significant_obstructive_cad_present","contributing_factors":[{"feature_name":"age","contribution_direction":"increases"}]}
```
Success returns summary, prediction_interpretation, contributing_factors (each with
plain_language_explanation), limitations, recommended_next_step, disclaimer and
prompt_version=explanation-v1. Error example: HTTP 503 with
{"code":"AI_UNAVAILABLE","detail":"AI explanation is unavailable."}.

## Tests and limitations
Verification on 2026-11-26: `pytest backend/tests -q` passed 629 tests and skipped 15
existing conditional tests on Windows. Linux/GitHub Actions verification remains
outstanding because no usable Linux runtime was available. The frontend suite passed
136 tests; TypeScript, production build, Python compilation and dependency audits passed.
OpenAI SDK 2.8.1 was installed and executed locally. AsyncOpenAI initialization and
chat.completions.parse with Pydantic structured output, refusal and incomplete response
handling were exercised using a synthetic HTTP transport. Timeout and rate-limit
exception mappings were covered by backend tests. No live OpenAI request was made, so
provider compatibility remains unverified.

The endpoint accepts only a signed capability, not client-supplied result fields. The
signed token authenticates but does not encrypt its derived prediction data. It is a
short-lived bearer credential and must be treated as sensitive. Provider requests use
bounded timeouts, no SDK retries, and do not log provider exception contents. Enabling
public access still requires privacy review and a deployment with durable shared quotas.


## Security hardening update
Prediction provenance: predict_endpoint issues X-Explanation-Token only after successful
model inference and explanation. Existing prediction JSON is unchanged. The frontend
keeps this header in memory and submits only {"token":"..."}. Tokens contain derived
probability, outcome and directions, a random nonce, fixed audience and five-minute
expiry. They are HMAC-SHA256 signed with AI_SIGNING_KEY (minimum 32 characters).
They are authenticated, NOT encrypted: treat the token as sensitive bearer data.
security.verify checks signature in constant time, expiry, audience and strict schemas.
No client-provided prediction fields or arbitrary instructions are accepted.

security.reserve uses SQLite BEGIN IMMEDIATE to atomically allow at most three provider
attempts per token. Failed attempts release the in-flight lock for a retry; successful
tokens are permanently replay-rejected. Every provider attempt counts toward the
configurable daily (50) and per-minute (5) global quotas. Only token hashes, timestamps
and attempt-state metadata are persisted for one day. AI_USAGE_DB must be persistent and
shared across workers. Failure to access usage storage fails closed before provider
invocation. Public users can exhaust this shared quota; authentication and fair per-user
allocation are not added. Multiple hosts with separate databases do not share quotas.
The feature is forcibly unavailable when VERCEL is set: do not enable serverless
deployment until shared durable atomic usage storage replaces SQLite. This explicitly
supersedes earlier one-shot retry and enablement descriptions.

No tests were deleted, skipped or weakened for this change. The Windows backend run
completed successfully; the prior Windows event-loop limitation did not recur in that
run. The required compatible Linux or GitHub Actions run remains outstanding. The local
SDK transport check validates SDK parsing behavior only and does not establish live
provider compatibility.
