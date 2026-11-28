"""Synthetic accounts, real Argon2/JWT and Redis Lua execution; no external providers."""
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import fakeredis
import jwt
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.auth import security as auth
from backend.app.api.endpoints import accounts
from backend.app.core.config import settings
from backend.app.db.orm import Base, Role, User, RefreshSession, session
from backend.app.services import shared


@pytest.fixture
def shared_store(monkeypatch):
    store = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(shared, "redis", lambda: store)
    monkeypatch.setattr(settings, "REDIS_URL", SecretStr("redis://localhost:6379/15"))
    return store


@pytest.fixture
def account_api(monkeypatch, shared_store):
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "APP_ORIGIN", "http://testserver")
    monkeypatch.setattr(settings, "DATABASE_URL", SecretStr("postgresql://test:test@localhost/cv_test"))
    monkeypatch.setattr(settings, "JWT_SIGNING_KEY", SecretStr("synthetic-signing-key-"*3))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(name=n) for n in ("viewer", "researcher", "admin")])
        db.commit()
    def database():
        with Session(engine, expire_on_commit=False) as db:
            yield db
    api = FastAPI()
    from backend.app.api.endpoints import imports, payments, oauth, maintenance, realtime
    from backend.app.api.body_limit import WorkspaceBodyLimit
    for router in (imports.router, payments.router, oauth.router, maintenance.router, realtime.router):
        api.include_router(router, prefix="/api/v1")
    api.add_middleware(WorkspaceBodyLimit)
    monkeypatch.setattr(realtime, "engine", lambda url: engine)
    api.include_router(accounts.router, prefix="/api/v1")
    api.dependency_overrides[session] = database
    with TestClient(api, headers={"Origin": "http://testserver"}) as client:
        yield client, engine
    engine.dispose()


def register(client, email="researcher@example.test"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": "synthetic-password-123"})


def test_argon2_policy():
    hashed = auth.password_hash("synthetic-password-123")
    assert hashed.startswith("$argon2id$")
    assert auth.password_matches("synthetic-password-123", hashed)
    assert not auth.password_matches("wrong", hashed)
    assert not auth.password_matches("anything", None)
    with pytest.raises(HTTPException):
        auth.password_hash("weak")


def test_registration_refresh_replay_and_role_guard(account_api):
    client, engine = account_api
    response = register(client)
    assert response.status_code == 201
    access = response.json()["access_token"]
    refresh = client.cookies.get(auth.COOKIE)
    headers = {"Authorization": "Bearer "+access}
    assert client.get("/api/v1/auth/me", headers=headers).json()["roles"] == ["viewer"]
    assert client.get("/api/v1/admin/users", headers=headers).status_code == 403
    assert client.get("/api/v1/admin/users").status_code == 401
    with Session(engine) as db:
        stored = db.scalar(select(RefreshSession))
        assert stored.token_hash == shared.digest(refresh) and stored.token_hash != refresh
        assert db.scalar(select(User)).password_hash.startswith("$argon2id$")
    assert client.post("/api/v1/auth/refresh").status_code == 200
    assert client.cookies.get(auth.COOKIE) != refresh
    client.cookies.clear()
    client.cookies.set(auth.COOKIE, refresh)
    assert client.post("/api/v1/auth/refresh").status_code == 401
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


@pytest.mark.parametrize("change", [{"exp": 0}, {"nbf": 9999999999}, {"aud": "wrong"}, {"iss": "wrong"}, {"jti": "not-uuid"}])
def test_jwt_claims_rejected(account_api, change):
    client, _ = account_api
    token = register(client).json()["access_token"]
    claims = jwt.decode(token, options={"verify_signature": False})
    claims.update(change)
    altered = jwt.encode(claims, settings.require_secret("JWT_SIGNING_KEY"), algorithm="HS256")
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer "+altered}).status_code == 401


def test_jwt_signature_algorithm_and_role_claims(account_api):
    client, engine = account_api
    token = register(client).json()["access_token"]
    claims = jwt.decode(token, options={"verify_signature": False})
    claims["roles"] = ["admin"]
    for algorithm, key in (("none", ""), ("HS384", settings.require_secret("JWT_SIGNING_KEY")), ("HS256", "wrong"*10)):
        forged = jwt.encode(claims, key, algorithm=algorithm)
        assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer "+forged}).status_code == 401
    # Even a signed role claim cannot override authoritative database roles.
    forged = jwt.encode(claims, settings.require_secret("JWT_SIGNING_KEY"), algorithm="HS256")
    assert client.get("/api/v1/admin/users", headers={"Authorization": "Bearer "+forged}).status_code == 403
    with Session(engine) as db:
        user = db.scalar(select(User))
        user.roles = [db.get(Role, "admin")]
        db.commit()
    assert client.get("/api/v1/admin/users", headers={"Authorization": "Bearer "+token}).status_code == 200


def test_password_change_revokes_and_origin_required(account_api):
    client, _ = account_api
    token = register(client).json()["access_token"]
    headers = {"Authorization": "Bearer "+token}
    assert client.post("/api/v1/auth/refresh", headers={"Origin": "https://evil.test"}).status_code == 403
    assert client.post("/api/v1/auth/password", headers=headers, json={"current_password": "synthetic-password-123", "new_password": "replacement-password-456"}).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "researcher@example.test", "password": "replacement-password-456"}).status_code == 200


def test_rate_limit_concurrency_ttl_and_outage(shared_store, monkeypatch):
    def attempt(_):
        try:
            shared.limit("test", "identity", 5, 60)
            return True
        except HTTPException as exc:
            assert exc.status_code == 429 and int(exc.headers["Retry-After"]) > 0
            return False
    with ThreadPoolExecutor(max_workers=10) as pool:
        assert sum(pool.map(attempt, range(20))) == 5
    assert 0 < shared_store.ttl("cv:limit:test:"+shared.digest("identity")) <= 60
    monkeypatch.setattr(shared, "redis", lambda: (_ for _ in ()).throw(ConnectionError()))
    with pytest.raises(HTTPException) as error:
        shared.limit("test", "identity")
    assert error.value.status_code == 503


def test_cache_hit_invalidation_and_unavailable(shared_store, monkeypatch):
    assert shared.cache_read() is None
    shared.cache_write({"evaluations": []})
    assert shared.cache_read() == {"evaluations": []}
    assert 0 < shared_store.ttl(shared.CACHE_KEY) <= 300
    shared.invalidate_research()
    assert shared.cache_read() is None
    monkeypatch.setattr(shared, "redis", lambda: (_ for _ in ()).throw(ConnectionError()))
    assert shared.cache_read() is None
    shared.cache_write({})


def test_shared_ai_replay_concurrent_and_retry(shared_store):
    from backend.app.ai import security
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(security.reserve, ["synthetic-derived-token"]*8)) == 1
    security.complete("synthetic-derived-token", False)
    assert security.reserve("synthetic-derived-token")
    security.complete("synthetic-derived-token", True)
    assert not security.reserve("synthetic-derived-token")
    assert "synthetic-derived-token" not in str(shared_store.keys())


def test_serverless_ai_requires_shared_config(monkeypatch):
    from backend.app.ai.client import available
    monkeypatch.setenv("VERCEL", "1")
    for key, value in {"LLM_ENABLED": True, "AI_SIGNING_KEY": SecretStr("a"*32), "OPENAI_API_KEY": SecretStr("synthetic"), "OPENAI_MODEL": "configured-model", "REDIS_URL": None}.items():
        monkeypatch.setattr(settings, key, value)
    assert not available()
    monkeypatch.setattr(settings, "REDIS_URL", SecretStr("redis://localhost"))
    assert available()
