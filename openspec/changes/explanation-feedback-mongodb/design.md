# Design: Anonymous explanation feedback in MongoDB

## Document
```
{ _id: ObjectId, helpful: bool, section: "summary" | "why" | "audit", model_version: "1.1.1",
  created_at: datetime, updated_at: datetime, edit_token_hash: "<sha256 hex>" }
```
The edit token (`secrets.token_urlsafe(24)`) is returned once at creation. Only its SHA-256 is stored; checks use
`hmac.compare_digest`. Reads never return the hash.

## Endpoints and status codes
| Operation | Request | Success | Errors |
|---|---|---|---|
| Create | `POST /feedback` | 201 + `Location`, body includes `edit_token` | 422 invalid body |
| Read one | `GET /feedback/{id}` | 200 | 404 unknown or malformed id |
| Read summary | `GET /feedback/summary` | 200, counts per section (aggregation pipeline) | — |
| Update | `PATCH /feedback/{id}` + `X-Edit-Token` | 200 | 401 no token, 403 wrong token, 404, 422 |
| Delete | `DELETE /feedback/{id}` + `X-Edit-Token` | 204 | 401, 403, 404 |
Any operation returns 503 `feedback_store_not_configured` when `MONGODB_URI` is unset and
`feedback_store_unavailable` when MongoDB cannot be reached.

## Connection
`MONGODB_URI` comes from `settings.require_secret`. `pymongo` is imported lazily; one `MongoClient` per process
(thread-safe, reused across warm serverless invocations) with short server-selection and socket timeouts. The
database is the URI's default database, or `cardiovanta` when the URI names none.
