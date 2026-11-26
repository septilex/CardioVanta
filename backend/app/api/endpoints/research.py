"""GET /api/v1/research/evaluations: research evaluation metadata from PostgreSQL (no patient data)."""
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.core.config import MissingSecretError
from backend.app.db.postgres import ResearchDatabaseUnavailable
from backend.app.db.research import research_evaluations

logger = logging.getLogger(__name__)
router = APIRouter()

NOT_CONFIGURED = "research_database_not_configured"
UNAVAILABLE = "research_database_unavailable"


def _unavailable(code: str, detail: str) -> JSONResponse:
    # 503: the request is valid, but the service behind it is not available right now.
    return JSONResponse(status_code=503, content={"detail": detail, "code": code},
                        headers={"Cache-Control": "no-store", "Retry-After": "60"})


@router.get("/research/evaluations")
def get_research_evaluations():
    try:
        data = research_evaluations()
    except MissingSecretError:
        logger.warning("Research evaluations requested but DATABASE_URL is not configured")
        return _unavailable(NOT_CONFIGURED, "The research database is not configured.")
    except ResearchDatabaseUnavailable as e:
        logger.error("Research database unavailable: %s", e)
        return _unavailable(UNAVAILABLE, "The research database is temporarily unavailable.")
    return JSONResponse(content=data, headers={"Cache-Control": "public, max-age=300"})
