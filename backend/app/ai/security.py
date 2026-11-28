"""Signed, expiring derived results; persistent atomic usage reservations."""
import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from pydantic import Field
from .schemas import StrictModel, ExplanationRequest
from backend.app.core.config import settings

MAX_TOKEN_ATTEMPTS = 3

class TokenRequest(StrictModel):
    token: str = Field(min_length=1, max_length=7000)

class Claims(StrictModel):
    audience: str
    expires: int
    nonce: str
    data: ExplanationRequest

def key() -> bytes:
    value = settings.require_secret("AI_SIGNING_KEY").encode()
    if len(value) < 32:
        raise ValueError("Signing configuration unavailable")
    return value

def encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")

def issue(data: ExplanationRequest) -> str:
    claims = Claims(audience="cardiovanta-explanation-v1", expires=int(time.time())+300,
                    nonce=secrets.token_hex(16), data=data)
    payload = encode(claims.model_dump_json().encode())
    signature = encode(hmac.digest(key(), payload.encode(), "sha256"))
    return payload+"."+signature

def verify(token: str) -> Claims:
    try:
        payload, signature = token.split(".")
        expected = encode(hmac.digest(key(), payload.encode(), "sha256"))
        if not hmac.compare_digest(signature, expected):
            raise ValueError()
        claims = Claims.model_validate_json(base64.urlsafe_b64decode(payload + "="*(-len(payload)%4)))
        now = int(time.time())
        if claims.audience != "cardiovanta-explanation-v1" or not now < claims.expires <= now+300:
            raise ValueError()
        if len(claims.nonce) != 32:
            raise ValueError()
        return claims
    except Exception:
        raise ValueError("Invalid prediction token") from None

def reserve(token: str) -> bool:
    """Atomically claim one bounded provider attempt for a signed token."""
    if settings.REDIS_URL:
        return reserve_shared(token)
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
    if settings.REDIS_URL:
        from backend.app.services.shared import redis
        result = redis().eval(COMPLETE_SCRIPT, 1, shared_token_key(token), int(succeeded))
        if not result:
            raise ValueError("Usage reservation unavailable")
        return
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


# All keys share a Redis Cluster hash slot. The budget counts attempts, including failures.
RESERVE_SCRIPT = """
if redis.call('HGET', KEYS[1], 'done') == '1' or redis.call('HGET', KEYS[1], 'busy') == '1' then return 0 end
if tonumber(redis.call('HGET', KEYS[1], 'attempts') or '0') >= 3 then return 0 end
if tonumber(redis.call('GET', KEYS[2]) or '0') >= tonumber(ARGV[1]) then return 0 end
if tonumber(redis.call('GET', KEYS[3]) or '0') >= tonumber(ARGV[2]) then return 0 end
redis.call('HINCRBY', KEYS[1], 'attempts', 1)
redis.call('HSET', KEYS[1], 'busy', 1)
redis.call('EXPIRE', KEYS[1], 600)
if redis.call('INCR', KEYS[2]) == 1 then redis.call('EXPIRE', KEYS[2], 86400) end
if redis.call('INCR', KEYS[3]) == 1 then redis.call('EXPIRE', KEYS[3], 60) end
return 1
"""
COMPLETE_SCRIPT = """
if redis.call('HGET', KEYS[1], 'busy') ~= '1' then return 0 end
redis.call('HSET', KEYS[1], 'busy', 0)
if ARGV[1] == '1' then redis.call('HSET', KEYS[1], 'done', 1) end
return 1
"""


def shared_token_key(token: str) -> str:
    return "cv:{ai}:token:" + hashlib.sha256(token.encode()).hexdigest()


def reserve_shared(token: str) -> bool:
    from backend.app.services.shared import redis
    if settings.AI_DAILY_LIMIT < 1 or settings.AI_MINUTE_LIMIT < 1:
        raise ValueError("Usage control unavailable")
    return bool(redis().eval(RESERVE_SCRIPT, 3, shared_token_key(token), "cv:{ai}:daily", "cv:{ai}:minute",
                             settings.AI_DAILY_LIMIT, settings.AI_MINUTE_LIMIT))
