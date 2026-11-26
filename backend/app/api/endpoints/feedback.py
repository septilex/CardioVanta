"""
Anonymous explanation feedback: create, read, update and delete MongoDB documents.

    POST   /api/v1/feedback            201 Created + Location, returns a one-time edit token
    GET    /api/v1/feedback/summary    200, counts per section (aggregation pipeline)
    GET    /api/v1/feedback/{id}       200, or 404
    PATCH  /api/v1/feedback/{id}       200; needs X-Edit-Token (401 missing, 403 wrong), 404
    DELETE /api/v1/feedback/{id}       204; needs X-Edit-Token (401 missing, 403 wrong), 404

503 when MongoDB is not configured or unreachable. No personal or clinical data is accepted: the request models
forbid any field outside the schema.
"""
import logging
from typing import Any, Callable, Literal, Optional

from fastapi import APIRouter, Header, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.config import MissingSecretError
from backend.app.db import mongo

logger = logging.getLogger(__name__)
router = APIRouter()

Section = Literal["summary", "why", "audit"]
NOT_CONFIGURED = "feedback_store_not_configured"
UNAVAILABLE = "feedback_store_unavailable"


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    helpful: bool
    section: Section
    model_version: str = Field(pattern=r"^\d+\.\d+\.\d+$", max_length=20)


class FeedbackUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    helpful: Optional[bool] = None
    section: Optional[Section] = None


def _error(status: int, detail: str, code: Optional[str] = None) -> JSONResponse:
    body = {"detail": detail}
    if code:
        body["code"] = code
    headers = {"Cache-Control": "no-store"}
    if status == 503:
        headers["Retry-After"] = "60"
    return JSONResponse(status_code=status, content=body, headers=headers)


def _with_store(action: Callable[[Any], Any]) -> Any:
    """Run an action against the collection, mapping configuration and connection failures to 503."""
    from pymongo.errors import PyMongoError

    try:
        return action(mongo.collection())
    except MissingSecretError:
        logger.warning("Feedback requested but MONGODB_URI is not configured")
        return _error(503, "The feedback store is not configured.", NOT_CONFIGURED)
    except PyMongoError as e:
        logger.error("Feedback store unavailable (%s)", type(e).__name__)
        return _error(503, "The feedback store is temporarily unavailable.", UNAVAILABLE)


def _object_id(feedback_id: str) -> Optional[Any]:
    from bson import ObjectId

    return ObjectId(feedback_id) if ObjectId.is_valid(feedback_id) else None


def _authorise(col: Any, feedback_id: str, token: Optional[str]) -> Any:
    """The stored document, or an error response: 404 unknown id, 401 no token, 403 wrong token."""
    oid = _object_id(feedback_id)
    doc = col.find_one({"_id": oid}) if oid is not None else None
    if doc is None:
        return _error(404, "Feedback not found.")
    if not token:
        return _error(401, "An X-Edit-Token header is required to change feedback.")
    if not mongo.token_matches(token, doc["edit_token_hash"]):
        return _error(403, "The edit token does not match this feedback.")
    return doc


@router.post("/feedback", status_code=201)
def create_feedback(payload: FeedbackCreate, response: Response):
    def action(col):
        token, digest = mongo.new_edit_token()
        stamp = mongo.now()
        doc = {**payload.model_dump(), "created_at": stamp, "updated_at": stamp, "edit_token_hash": digest}
        doc["_id"] = col.insert_one(doc).inserted_id
        body = {**mongo.public_view(doc), "edit_token": token}
        return JSONResponse(status_code=201, content=body,
                            headers={"Location": f"/api/v1/feedback/{doc['_id']}", "Cache-Control": "no-store"})

    return _with_store(action)


@router.get("/feedback/summary")
def feedback_summary():
    def action(col):
        pipeline = [
            {"$group": {"_id": "$section", "total": {"$sum": 1},
                        "helpful": {"$sum": {"$cond": ["$helpful", 1, 0]}}}},
            {"$sort": {"_id": 1}},
        ]
        sections = [{"section": row["_id"], "total": row["total"], "helpful": row["helpful"]}
                    for row in col.aggregate(pipeline)]
        return {"sections": sections, "total": sum(s["total"] for s in sections)}

    return _with_store(action)


@router.get("/feedback/{feedback_id}")
def read_feedback(feedback_id: str):
    def action(col):
        oid = _object_id(feedback_id)
        doc = col.find_one({"_id": oid}) if oid is not None else None
        if doc is None:
            return _error(404, "Feedback not found.")
        return mongo.public_view(doc)

    return _with_store(action)


@router.patch("/feedback/{feedback_id}")
def update_feedback(feedback_id: str, payload: FeedbackUpdate,
                    x_edit_token: Optional[str] = Header(default=None)):
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        return _error(422, "Provide at least one of: helpful, section.")

    def action(col):
        doc = _authorise(col, feedback_id, x_edit_token)
        if isinstance(doc, JSONResponse):
            return doc
        changes["updated_at"] = mongo.now()
        updated = col.find_one_and_update({"_id": doc["_id"]}, {"$set": changes},
                                          return_document=True)
        return mongo.public_view(updated)

    return _with_store(action)


@router.delete("/feedback/{feedback_id}", status_code=204)
def delete_feedback(feedback_id: str, x_edit_token: Optional[str] = Header(default=None)):
    def action(col):
        doc = _authorise(col, feedback_id, x_edit_token)
        if isinstance(doc, JSONResponse):
            return doc
        col.delete_one({"_id": doc["_id"]})
        return Response(status_code=204)

    return _with_store(action)
