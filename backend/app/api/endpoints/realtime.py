"""Authenticated import snapshots from durable PostgreSQL, portable across serverless instances."""
import asyncio
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from backend.app.auth import security as auth
from backend.app.core.config import settings
from backend.app.db.orm import engine, UploadBatch
from backend.app.services.shared import limit

router = APIRouter()


class Hello(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=3000)


def snapshot(token, batch_id):
    with Session(engine(settings.require_secret("DATABASE_URL"))) as db:
        user = auth.user_for_token(token, db)
        if not {r.name for r in user.roles}.intersection({"admin", "researcher"}):
            raise HTTPException(403)
        batch = db.get(UploadBatch, batch_id)
        if not batch or batch.user_id != user.id:
            raise HTTPException(404)
        return {"type": "status", "id": str(batch.id), "status": batch.status, "row_count": batch.row_count}


@router.websocket("/research/imports/{batch_id}/live")
async def live(websocket: WebSocket, batch_id: uuid.UUID):
    if not settings.REALTIME_ENABLED or not auth.enabled() or websocket.headers.get("origin") != settings.APP_ORIGIN.rstrip("/"):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=5)
        if len(raw) > 4096:
            raise ValueError()
        hello = Hello.model_validate_json(raw)
        claims = auth.verify_access(hello.token)
        await run_in_threadpool(limit, "socket", claims["sub"], 30, 60)
        last = None
        for tick in range(240):  # reconnect before the configured serverless duration limit
            state = await run_in_threadpool(snapshot, hello.token, batch_id)
            if state != last:
                await websocket.send_json(state)
                last = state
            elif tick % 10 == 0:
                await websocket.send_json({"type": "heartbeat"})
            if state["status"] in ("completed", "failed"):
                await websocket.close(code=1000)
                return
            await asyncio.sleep(1)
        await websocket.close(code=1012)
    except WebSocketDisconnect:
        pass
    except (HTTPException, ValueError, TimeoutError):
        await websocket.close(code=1008)
    except Exception:
        await websocket.close(code=1011)
