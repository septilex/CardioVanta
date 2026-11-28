"""Redis counters and public research caching. Never stores clinical data or raw tokens."""
import hashlib
import json
from functools import lru_cache

from fastapi import HTTPException, Request
from redis import Redis

from backend.app.core.config import settings

CACHE_KEY = "cv:research:evaluations:v1"
# INCR and expiry are inseparable, including under simultaneous requests.
LIMIT_SCRIPT = """
local n = redis.call('INCR', KEYS[1])
if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {n, redis.call('TTL', KEYS[1])}
"""


@lru_cache(maxsize=4)
def _connection(url: str) -> Redis:
    return Redis.from_url(url, decode_responses=True, socket_timeout=2, socket_connect_timeout=2)


def redis() -> Redis:
    return _connection(settings.require_secret("REDIS_URL"))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def limit(scope: str, identity: str, maximum: int = 10, seconds: int = 60) -> None:
    try:
        count, ttl = redis().eval(LIMIT_SCRIPT, 1, f"cv:limit:{scope}:{digest(identity)}", seconds)
    except Exception:
        raise HTTPException(503, "Shared usage controls are unavailable.", headers={"Retry-After": "60"}) from None
    if count > maximum:
        raise HTTPException(429, "Too many requests. Try again later.", headers={"Retry-After": str(max(1, ttl))})


def anonymous_id(request: Request) -> str:
    # Do not trust arbitrary forwarded IP headers. Configure the ASGI proxy trust boundary explicitly.
    return request.client.host if request.client else "unknown"


def cache_read():
    if not settings.REDIS_URL:
        return None
    try:
        value = redis().get(CACHE_KEY)
        return json.loads(value) if value else None
    except Exception:
        return None  # Caching is optional; authorization/rate limiting is fail-closed.


def cache_write(data):
    if settings.REDIS_URL:
        try:
            redis().set(CACHE_KEY, json.dumps(data), ex=max(1, settings.RESEARCH_CACHE_TTL))
        except Exception:
            pass


def invalidate_research():
    redis().delete(CACHE_KEY)
