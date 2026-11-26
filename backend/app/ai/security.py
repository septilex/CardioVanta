"""Signed, expiring derived results; persistent atomic usage reservations."""
import hashlib
import secrets
import sqlite3
import time
from typing import Literal
import jwt
from pydantic import Field
from .schemas import StrictModel, ExplanationRequest
from backend.app.core.config import settings

MAX_TOKEN_ATTEMPTS = 3

class TokenRequest(StrictModel):
    token: str = Field(min_length=1, max_length=7000)

class Claims(StrictModel):
    iss: Literal["cardiovanta-ai-explanation"]
    aud: Literal["cardiovanta-explanation-v1"]
    iat: int
    exp: int
    jti: str = Field(pattern=r"^[0-9a-f]{32}$")
    data: ExplanationRequest

def key() -> bytes:
    value = settings.require_secret("AI_SIGNING_KEY").encode()
    if len(value) < 32:
        raise ValueError("Signing configuration unavailable")
    return value

def issue(data: ExplanationRequest) -> str:
    issued = int(time.time())
    claims = Claims(iss="cardiovanta-ai-explanation", aud="cardiovanta-explanation-v1",
                    iat=issued, exp=issued+300, jti=secrets.token_hex(16), data=data)
    return jwt.encode(claims.model_dump(mode="json"), key(), algorithm="HS256", headers={"typ": "JWT"})

def verify(token: str) -> Claims:
    try:
        if not isinstance(token, str) or len(token) > 7000:
            raise ValueError()
        payload = jwt.decode(
            token, key(), algorithms=["HS256"], audience="cardiovanta-explanation-v1",
            issuer="cardiovanta-ai-explanation",
            options={"require": ["iss", "aud", "iat", "exp", "jti", "data"], "verify_iat": True},
        )
        claims = Claims.model_validate(payload)
        now = int(time.time())
        if claims.iat > now or not now < claims.exp <= claims.iat+300:
            raise ValueError()
        return claims
    except Exception:
        raise ValueError("Invalid prediction token") from None

def reserve(token: str) -> bool:
    """Atomically claim one bounded provider attempt for a signed token."""
    if not settings.AI_USAGE_DB or settings.AI_DAILY_LIMIT < 1 or settings.AI_MINUTE_LIMIT < 1:
        raise ValueError("Usage control unavailable")
    now = int(time.time())
    with sqlite3.connect(settings.AI_USAGE_DB, timeout=2) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS ai_usage (
            digest TEXT PRIMARY KEY, created INTEGER NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 1, succeeded INTEGER NOT NULL DEFAULT 1,
            in_flight INTEGER NOT NULL DEFAULT 0)""")
        # Rows created by the previous one-shot implementation are treated as
        # completed, preserving replay protection across an in-place upgrade.
        columns = {row[1] for row in db.execute("PRAGMA table_info(ai_usage)")}
        if "attempts" not in columns:
            db.execute("ALTER TABLE ai_usage ADD COLUMN attempts INTEGER NOT NULL DEFAULT 1")
        if "succeeded" not in columns:
            db.execute("ALTER TABLE ai_usage ADD COLUMN succeeded INTEGER NOT NULL DEFAULT 1")
        if "in_flight" not in columns:
            db.execute("ALTER TABLE ai_usage ADD COLUMN in_flight INTEGER NOT NULL DEFAULT 0")
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM ai_usage WHERE created < ?", (now-86400,))
        digest = hashlib.sha256(token.encode()).hexdigest()
        row = db.execute("SELECT attempts, succeeded, in_flight FROM ai_usage WHERE digest=?", (digest,)).fetchone()
        if row:
            attempts, succeeded, in_flight = row
            if succeeded or in_flight or attempts >= MAX_TOKEN_ATTEMPTS:
                return False
            daily = db.execute("SELECT coalesce(sum(attempts),0) FROM ai_usage").fetchone()[0]
            minute = db.execute("SELECT coalesce(sum(attempts),0) FROM ai_usage WHERE created > ?", (now-60,)).fetchone()[0]
            if daily >= settings.AI_DAILY_LIMIT or minute >= settings.AI_MINUTE_LIMIT:
                return False
            db.execute("UPDATE ai_usage SET attempts=attempts+1, in_flight=1 WHERE digest=?", (digest,))
            return True
        daily = db.execute("SELECT coalesce(sum(attempts),0) FROM ai_usage").fetchone()[0]
        minute = db.execute("SELECT coalesce(sum(attempts),0) FROM ai_usage WHERE created > ?", (now-60,)).fetchone()[0]
        if daily >= settings.AI_DAILY_LIMIT or minute >= settings.AI_MINUTE_LIMIT:
            return False
        db.execute("INSERT INTO ai_usage (digest, created, attempts, succeeded, in_flight) VALUES (?,?,1,0,1)", (digest, now))
    return True

def complete(token: str, succeeded: bool) -> None:
    """Release an attempt; permanently lock a token after a successful response."""
    if not settings.AI_USAGE_DB:
        raise ValueError("Usage control unavailable")
    digest = hashlib.sha256(token.encode()).hexdigest()
    with sqlite3.connect(settings.AI_USAGE_DB, timeout=2) as db:
        cursor = db.execute(
            "UPDATE ai_usage SET succeeded=CASE WHEN ? THEN 1 ELSE succeeded END, in_flight=0 WHERE digest=? AND in_flight=1",
            (int(succeeded), digest),
        )
        if cursor.rowcount != 1:
            raise ValueError("Usage reservation unavailable")
