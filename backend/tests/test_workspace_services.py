"""Real service integration. CI MUST supply PostgreSQL, Mongo replica set and Redis URLs."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.tests.ci_env import needs_database, require_database_url, assert_ci_provides
from backend.app.core.config import Settings, settings
from backend.app.db.orm import engine, session, User, Role, RefreshSession
from backend.app.db.migrate import apply_migrations
from backend.app.services import shared


def test_ci_provides_all_services():
    for name in ("TEST_DATABASE_URL", "TEST_MONGODB_URI", "TEST_REDIS_URL"):
        assert_ci_provides(name)


@needs_database("TEST_REDIS_URL")
def test_real_redis_atomic_rate_cache_expiry_and_ai(monkeypatch):
    require_database_url("TEST_REDIS_URL")
    url = os.environ["TEST_REDIS_URL"]
    assert urlparse(url).path == "/15", "Use dedicated Redis database 15 for integration tests"
    monkeypatch.setattr(settings, "REDIS_URL", SecretStr(url))
    store = shared.redis()
    keys = list(store.scan_iter("cv:*"))
    if keys: store.delete(*keys)
    def attempt(_):
        from fastapi import HTTPException
        try:
            shared.limit("concurrent", "synthetic", 7)
            return True
        except HTTPException as error:
            assert error.status_code == 429
            return False
    with ThreadPoolExecutor(max_workers=16) as pool:
        assert sum(pool.map(attempt, range(40))) == 7
    shared.cache_write({"evaluations": []})
    assert shared.cache_read() == {"evaluations": []}
    store.pexpire(shared.CACHE_KEY, 1)
    import time
    time.sleep(.02)
    assert shared.cache_read() is None
    shared.cache_write({"evaluations": []})
    shared.invalidate_research()
    assert shared.cache_read() is None
    from backend.app.ai import security
    with ThreadPoolExecutor(max_workers=12) as pool:
        assert sum(pool.map(security.reserve, ["real-redis-synthetic-token"]*12)) == 1
    security.complete("real-redis-synthetic-token", True)
    assert not security.reserve("real-redis-synthetic-token")


@pytest.fixture
def postgres_schema(monkeypatch):
    require_database_url("TEST_DATABASE_URL")
    import psycopg
    from psycopg import sql
    url = os.environ["TEST_DATABASE_URL"]
    assert urlparse(url).path.endswith("_test"), "Use a dedicated *_test database"
    name = "viva_"+uuid.uuid4().hex
    with psycopg.connect(url, autocommit=True) as db:
        db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(name)))
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query)); query["options"] = "-csearch_path="+name
    scoped = urlunparse(parsed._replace(query=urlencode(query)))
    cfg = Settings(_env_file=None, DATABASE_URL=scoped)
    assert len(apply_migrations(cfg)) == 3
    assert apply_migrations(cfg) == []
    monkeypatch.setattr(settings, "DATABASE_URL", SecretStr(scoped))
    yield engine(scoped)
    engine(scoped).dispose()
    with psycopg.connect(url, autocommit=True) as db:
        db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(name)))


@needs_database("TEST_DATABASE_URL")
@needs_database("TEST_REDIS_URL")
def test_real_postgres_orm_upload_rollback_and_refresh(postgres_schema, monkeypatch):
    from backend.app.api.endpoints import accounts, imports
    from backend.tests.test_workspace_workflows import CSV
    from backend.app.db.research import research_evaluations
    monkeypatch.setattr(settings, "REDIS_URL", SecretStr(os.environ["TEST_REDIS_URL"]))
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "JWT_SIGNING_KEY", SecretStr(uuid.uuid4().hex+uuid.uuid4().hex))
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(settings, "APP_ORIGIN", "http://testserver")
    api = FastAPI(); api.include_router(accounts.router, prefix="/api/v1"); api.include_router(imports.router, prefix="/api/v1")
    with TestClient(api, headers={"Origin": "http://testserver"}) as client:
        response = client.post("/api/v1/auth/register", json={"email": f"{uuid.uuid4()}@example.test", "password": "synthetic-password-123"})
        assert response.status_code == 201, response.text
        token = response.json()["access_token"]
        with Session(postgres_schema) as db:
            user = db.scalar(select(User)); user.roles = [db.get(Role, "researcher")]; db.commit()
            assert db.scalar(select(RefreshSession)).token_hash != client.cookies.get("cv_refresh")
        headers = {"Authorization": "Bearer "+token}
        csv = CSV.replace(b"synthetic,", b"cleveland_dev,")
        batch = client.post("/api/v1/research/imports", headers=headers).json()
        path = f"/api/v1/research/imports/{batch['id']}/file"
        assert client.post(path, files={"file": ("research.csv", csv, "text/csv")}, headers=headers).status_code == 200
        with postgres_schema.connect() as db:
            count = db.scalar(text("SELECT count(*) FROM metrics"))
        # First new metric is rolled back when the next row duplicates an existing metric.
        mixed = csv.replace(b"roc_auc,0.8", b"brier,0.2") + csv.splitlines()[1]+b"\n"
        batch = client.post("/api/v1/research/imports", headers=headers).json()
        assert client.post(f"/api/v1/research/imports/{batch['id']}/file", files={"file": ("research.csv", mixed, "text/csv")}, headers=headers).status_code == 409
        with postgres_schema.connect() as db:
            assert db.scalar(text("SELECT count(*) FROM metrics")) == count
        assert research_evaluations()  # Existing multi-table JOINs see the committed import.
        assert client.post("/api/v1/auth/refresh").status_code == 200


@needs_database("TEST_MONGODB_URI")
def test_real_mongo_validator_indexes_relations_and_delete(monkeypatch):
    require_database_url("TEST_MONGODB_URI")
    from backend.app.db import mongo
    from backend.app.db.mongo_setup import setup, EVENTS
    from backend.app.api.endpoints.feedback import router
    from pymongo.errors import WriteError
    from bson import ObjectId
    parsed = urlparse(os.environ["TEST_MONGODB_URI"])
    assert parsed.path.endswith("_test"), "Use a dedicated *_test Mongo database"
    uri = urlunparse(parsed._replace(path="/cv_"+uuid.uuid4().hex+"_test"))
    monkeypatch.setattr(settings, "MONGODB_URI", SecretStr(uri))
    col = mongo.collection()
    try:
        setup(); setup()
        api = FastAPI(); api.include_router(router, prefix="/api/v1")
        with TestClient(api) as client:
            created = client.post("/api/v1/feedback", json={"helpful": True, "section": "why", "model_version": "1.1.1"})
            assert created.status_code == 201, created.text
            data = created.json(); oid = ObjectId(data["id"])
            assert col.find_one()["metadata"] == {"surface": "assessment", "schema_version": 1}
            assert col.database[EVENTS].find_one()["feedback_id"] == oid
            invalid = {**col.find_one(), "_id": ObjectId(), "clinical_input": "forbidden"}
            with pytest.raises(WriteError): col.insert_one(invalid)
            bad = {**col.find_one(), "_id": ObjectId(), "section": "invalid"}
            with pytest.raises(WriteError): col.insert_one(bad)
            indexes = col.index_information()
            assert indexes["feedback_section_created"]["key"] == [("section", 1), ("created_at", -1)]
            assert indexes["feedback_version_created"]["key"] == [("model_version", 1), ("created_at", -1)]
            assert "events_parent_created" in col.database[EVENTS].index_information()
            # No hint: MongoDB's own planner must pick the index, and the index must supply the sort order.
            plan = str(col.find({"section": "why"}).sort("created_at", -1).explain()["queryPlanner"]["winningPlan"])
            assert "IXSCAN" in plan and "feedback_section_created" in plan and "'SORT'" not in plan, plan
            headers = {"X-Edit-Token": data["edit_token"]}
            assert client.patch(f"/api/v1/feedback/{oid}", json={"helpful": False}, headers=headers).status_code == 200
            assert col.database[EVENTS].count_documents({"feedback_id": oid}) == 2
            assert client.delete(f"/api/v1/feedback/{oid}", headers=headers).status_code == 204
            assert col.database[EVENTS].count_documents({"feedback_id": oid}) == 0
    finally:
        col.database.client.drop_database(col.database.name)


@needs_database("TEST_DATABASE_URL")
def test_real_postgres_planner_uses_the_declared_indexes(postgres_schema):
    """#43: with realistic row counts PostgreSQL's own planner chooses the indexes from migration 003."""
    with postgres_schema.begin() as db:
        owners = [uuid.uuid4() for _ in range(200)]
        db.execute(text("INSERT INTO users (id, email) SELECT u, u::text || '@example.test' FROM unnest(CAST(:ids AS uuid[])) AS u"),
                   {"ids": owners})
        # 20,000 synthetic sessions; about 1% have expired, which is what the daily clean-up deletes.
        db.execute(text("""
            INSERT INTO refresh_sessions (id, user_id, family, token_hash, expires_at)
            SELECT gen_random_uuid(), (CAST(:ids AS uuid[]))[1 + n % 200], gen_random_uuid(), md5(n::text) || md5((n + 1)::text),
                   now() + CASE WHEN n % 100 = 0 THEN interval '-1 day' ELSE interval '7 days' END
            FROM generate_series(1, 20000) AS n"""), {"ids": owners})
        db.execute(text("""
            INSERT INTO upload_batches (id, user_id, status, created_at)
            SELECT gen_random_uuid(), (CAST(:ids AS uuid[]))[1 + n % 200], 'completed', now() - n * interval '1 minute'
            FROM generate_series(1, 20000) AS n"""), {"ids": owners})
        db.execute(text("ANALYZE refresh_sessions; ANALYZE upload_batches"))
        expired = db.scalar(text("EXPLAIN (FORMAT JSON) SELECT id FROM refresh_sessions WHERE expires_at < now()"))
        owner = db.scalar(text("EXPLAIN (FORMAT JSON) SELECT id FROM upload_batches WHERE user_id = :u ORDER BY created_at DESC LIMIT 10"),
                          {"u": owners[0]})
    assert "refresh_sessions_expiry_idx" in str(expired), expired
    assert "upload_batches_owner_idx" in str(owner), owner
    assert "'Sort'" not in str(owner)  # the composite (user_id, created_at) index already returns rows in order


@needs_database("TEST_DATABASE_URL")
def test_real_postgres_cron_is_idempotent_under_concurrent_invocations(postgres_schema):
    """#51: overlapping cron deliveries serialize on the advisory lock; the day's work runs exactly once."""
    from backend.app.api.endpoints.maintenance import maintain
    from backend.app.db.orm import MaintenanceRun
    with postgres_schema.begin() as db:
        owner = uuid.uuid4()
        db.execute(text("INSERT INTO users (id, email) VALUES (:u, 'cron@example.test')"), {"u": owner})
        db.execute(text("""INSERT INTO refresh_sessions (id, user_id, family, token_hash, expires_at)
                           SELECT gen_random_uuid(), :u, gen_random_uuid(), md5(n::text) || md5((n + 7)::text),
                                  now() - interval '1 hour' FROM generate_series(1, 5) AS n"""), {"u": owner})

    def run(_):
        with Session(postgres_schema) as db:
            return maintain(db)

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(run, range(6)))
    assert sorted(r["status"] for r in results) == ["already_completed"] * 5 + ["completed"]
    assert {r["removed_sessions"] for r in results} == {5}  # every caller reports the single real run
    with Session(postgres_schema) as db:
        assert db.query(MaintenanceRun).count() == 1
        assert db.scalar(text("SELECT count(*) FROM refresh_sessions")) == 0
