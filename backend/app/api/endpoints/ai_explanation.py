"""Bound input before parsing; never expose validation input or provider details."""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from backend.app.ai import client
from backend.app.ai.schemas import ExplanationRequest, ExplanationResponse

from backend.app.ai.security import TokenRequest, verify, reserve, complete

router = APIRouter()
HEADERS = {"Cache-Control": "no-store"}

@router.get("/ai/status")
async def status():
    return JSONResponse({"enabled": client.available()}, headers=HEADERS)

@router.post("/ai/explanation", response_model=ExplanationResponse)
async def explanation(request: Request):
    if not client.available():
        return JSONResponse({"code": "AI_UNAVAILABLE", "detail": "AI explanation is unavailable."}, status_code=503, headers=HEADERS)
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > 8192:
            return JSONResponse({"code": "AI_INVALID_REQUEST", "detail": "Request is too large."}, status_code=422, headers=HEADERS)
        raw.extend(chunk)
    try:
        body = TokenRequest.model_validate_json(raw)
        claims = verify(body.token)
        data = claims.data
    except (ValidationError, ValueError):
        return JSONResponse({"code": "AI_INVALID_REQUEST", "detail": "Invalid explanation request."}, status_code=422, headers=HEADERS)
    reserved = False
    succeeded = False
    try:
        try:
            allowed = reserve(body.token)
        except Exception:
            raise client.ExplanationError(503, "AI_USAGE_UNAVAILABLE") from None
        if not allowed:
            raise client.ExplanationError(429, "AI_USAGE_LIMIT")
        reserved = True
        result = await client.explain(data)
        try:
            complete(body.token, succeeded=True)
            succeeded = True
        except Exception:
            raise client.ExplanationError(503, "AI_USAGE_UNAVAILABLE") from None
        return JSONResponse(result.model_dump(), headers=HEADERS)
    except client.ExplanationError as exc:
        return JSONResponse({"code": exc.code, "detail": "AI explanation could not be generated. Please try again later."}, status_code=exc.status, headers=HEADERS)
    finally:
        if reserved and not succeeded:
            try:
                complete(body.token, succeeded=False)
            except Exception:
                # Fail closed: an orphaned in-flight reservation cannot be replayed
                # until process/database recovery; never expose storage details.
                pass
