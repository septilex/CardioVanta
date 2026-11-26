# Tasks

## 1. Store and API
- [x] 1.1 `backend/app/db/mongo.py`: lazy client, collection access, document mapping.
- [x] 1.2 `backend/app/api/endpoints/feedback.py`: create, read, summary, update, delete with the status codes above.
- [x] 1.3 `pymongo` pinned in api and backend requirements.

## 2. Frontend
- [x] 2.1 Feedback control under the result explanation (create, change, withdraw).

## 3. Verification
- [x] 3.1 Tests without a database (503, 422, 404 paths) and against a throwaway MongoDB (full CRUD cycle).
- [x] 3.2 MongoDB service container in CI.
