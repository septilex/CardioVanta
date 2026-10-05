# Design

## Test Architecture
- **ML Framework Pytest Suite** (`tests/`): 73 distinct tests validating model behavior, generation, drift, and foundation.
- **Backend API Pytest Suite** (`backend/tests/`): 59 distinct tests validating FastAPI logic, schemas, and security.
- **Frontend Jest Suite** (`__tests__/`): 13 distinct tests validating React components and UI interactions.
- Total unique tests executed in CI: 145.

These suites do not overlap. They cover separate layers of the stack.
