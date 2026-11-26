# Proposal: Anonymous explanation feedback in MongoDB

## Why
The result page explains a modelled probability in three tabs (Result, Why, Technical audit). We have no
signal on whether those explanations help. A one-tap "Was this helpful?" control, which a person can change or
withdraw, measures that without collecting anything about the person or their health.

Feedback is a set of independent, self-contained documents with no relations and a shape that may grow (for
example a reason code later), which suits a document store. MongoDB also lets the project demonstrate full CRUD
against a real database, next to the relational research data in PostgreSQL.

## What Changes
- A `explanation_feedback` collection: `{helpful, section, model_version, created_at, updated_at, edit_token_hash}`.
- `POST /api/v1/feedback` (create, 201 + one-time edit token), `GET /api/v1/feedback/{id}` (read),
  `GET /api/v1/feedback/summary` (aggregate read), `PATCH /api/v1/feedback/{id}` (update) and
  `DELETE /api/v1/feedback/{id}` (delete, 204). Changing or deleting needs the edit token.
- A feedback control under the result explanation.
- Tests against a throwaway MongoDB (CI service container).

## Non-goals
- No clinical inputs, probabilities, free text, names, emails, IP addresses or other identifiers are stored.
  The model version is stored so feedback can be compared across versions; it is not about the person.
- No accounts or authentication. The edit token only lets the person who gave the feedback change it.
- Prediction serving never connects to MongoDB.
