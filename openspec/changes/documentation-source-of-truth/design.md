1. **README.md Overhaul**:
   - Delete obsolete `docker-compose.yml` deployment instructions.
   - Accurately describe the Vercel serverless deployment architecture.
   - Update testing instructions to reflect the unified root directory execution (`npm run test`, `pytest tests/`, `pytest backend/tests/`).
   - Remove references to non-existent scripts like `test.ps1`.
   - Maintain strict disclaimers preventing clinical use interpretation.
2. **Architecture Documentation (`docs/architecture.md`)**:
   - Update Next.js version reference to 16.3.8.
   - Explicitly mention the Vercel serverless monolithic architecture for backend/frontend routing instead of a generic static build.
3. **Deployment Documentation (`docs/deployment.md`)**:
   - Explicitly mention the `npm audit --audit-level=critical` policy utilized by the GitHub Actions CI workflow to address known unfixable high-severity dependencies safely.
4. **Cleanup**:
   - Delete obsolete Docker configuration files (`docker-compose.yml`, `backend/Dockerfile`, `.dockerignore`) to prevent future confusion.
