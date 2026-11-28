"""Idempotent daily maintenance; no research/feedback deletion or model modification."""
import hmac
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, select, text, update
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.orm import RefreshSession, OAuthFlow, UploadBatch, MaintenanceRun, session, now

router = APIRouter()


def authorize(request: Request):
    secret = settings.CRON_SECRET
    if not secret or len(secret.get_secret_value()) < 32:
        raise HTTPException(503, "Maintenance is not configured.")
    if not hmac.compare_digest(request.headers.get("authorization", ""), "Bearer "+secret.get_secret_value()):
        raise HTTPException(401, "Unauthorized maintenance request.")


def maintain(db: Session):
    day = now().date()
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(530051)"))
    existing = db.get(MaintenanceRun, day)
    if existing:
        return {"status": "already_completed", "date": str(day), "removed_sessions": existing.removed_sessions}
    removed = db.execute(delete(RefreshSession).where(RefreshSession.expires_at < now())).rowcount
    db.execute(delete(OAuthFlow).where(OAuthFlow.expires_at < now()))
    db.execute(update(UploadBatch).where(UploadBatch.created_at < now()-timedelta(days=1),
                                        UploadBatch.status.in_(["ready", "validating", "importing"])).values(status="failed"))
    db.add(MaintenanceRun(run_date=day, removed_sessions=removed))
    db.commit()
    return {"status": "completed", "date": str(day), "removed_sessions": removed}


@router.get("/maintenance/daily", dependencies=[Depends(authorize)])
def daily(db: Session = Depends(session)):
    try:
        return maintain(db)
    except Exception:
        db.rollback()
        raise HTTPException(503, "Maintenance could not complete. Safe to retry.") from None
