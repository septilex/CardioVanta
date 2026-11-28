import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.auth import security as auth
from backend.app.db.orm import User, UploadBatch, session
from backend.app.services import shared
from backend.app.services.imports import parse_csv, write_rows, MAX_BYTES

router = APIRouter()
researcher = auth.require_roles("researcher", "admin")


def batch_view(batch):
    return {"id": str(batch.id), "status": batch.status, "row_count": batch.row_count}


def owned_batch(db, batch_id, user, lock=False):
    query = select(UploadBatch).where(UploadBatch.id == batch_id, UploadBatch.user_id == user.id)
    batch = db.scalar(query.with_for_update() if lock else query)
    if not batch:
        raise HTTPException(404, "Import not found.")
    return batch


@router.post("/research/imports", status_code=201)
def create_batch(request: Request, user: User = Depends(researcher), db: Session = Depends(session)):
    auth.check_origin(request)
    shared.limit("import", str(user.id), 10, 300)
    batch = UploadBatch(user_id=user.id)
    db.add(batch)
    db.commit()
    return batch_view(batch)


@router.get("/research/imports/{batch_id}")
def batch_status(batch_id: uuid.UUID, user: User = Depends(researcher), db: Session = Depends(session)):
    return batch_view(owned_batch(db, batch_id, user))


@router.post("/research/imports/{batch_id}/file")
def upload(batch_id: uuid.UUID, request: Request, file: UploadFile = File(...),
           user: User = Depends(researcher), db: Session = Depends(session)):
    auth.check_origin(request)
    shared.limit("upload", str(user.id), 10, 300)
    batch = owned_batch(db, batch_id, user, lock=True)
    if batch.status != "ready":
        raise HTTPException(409, "This import has already started. Create a new import.")
    batch.status = "validating"
    db.commit()
    try:
        rows = parse_csv(file.file.read(MAX_BYTES+1), file.filename, file.content_type)
        batch.status = "importing"
        db.commit()
        write_rows(db, rows)
        batch.status, batch.row_count = "completed", len(rows)
        db.commit()
    except Exception as exc:
        db.rollback()
        batch = db.get(UploadBatch, batch_id)
        batch.status = "failed"
        db.commit()
        if isinstance(exc, HTTPException):
            raise
        if isinstance(exc, IntegrityError):
            raise HTTPException(409, "An evaluation metric already exists. No rows were imported.") from None
        raise HTTPException(503, "Import failed. No rows were imported.") from None
    finally:
        file.file.close()
    try:
        shared.invalidate_research()
    except Exception:
        # Commit is authoritative; cache remains bounded by TTL. Do not report the import as failed.
        return {**batch_view(batch), "notice": "Imported. Public research cache will refresh within five minutes."}
    return batch_view(batch)
