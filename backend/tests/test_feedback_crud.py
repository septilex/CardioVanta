"""
Anonymous explanation feedback in MongoDB (openspec/changes/explanation-feedback-mongodb).

Always run: validation (422), the 503 paths and token hashing, without a database.
With TEST_MONGODB_URI (a throwaway MongoDB; CI provides a service container): the full create, read, update and
delete cycle through the API, with every status code the design lists. No personal or clinical data.
"""
import os
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from backend.app.core.config import settings
from backend.app.db import mongo
from backend.app.main import app

TEST_MONGODB_URI = os.environ.get("TEST_MONGODB_URI", "").strip()
VALID = {"helpful": True, "section": "why", "model_version": "1.1.1"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def no_store(monkeypatch):
    monkeypatch.setattr(settings, "MONGODB_URI", None)
    mongo.reset_clients()


# --- no database needed ------------------------------------------------------------------------------------

@pytest.mark.parametrize("body", [
    {},                                                         # missing fields
    {**VALID, "helpful": "very"},                               # wrong type
    {**VALID, "section": "landing"},                            # not a result tab
    {**VALID, "model_version": "latest"},                       # not an exact version
    {**VALID, "comment": "I am 54 with chest pain"},            # free text is never accepted
    {**VALID, "age": 54},                                       # clinical input is never accepted
])
def test_invalid_feedback_is_rejected_before_any_storage(client, no_store, body):
    r = client.post("/api/v1/feedback", json=body)
    assert r.status_code == 422


@pytest.mark.parametrize("method,path,kwargs", [
    ("post", "/api/v1/feedback", {"json": VALID}),
    ("get", "/api/v1/feedback/summary", {}),
    ("get", "/api/v1/feedback/65a000000000000000000000", {}),
    ("patch", "/api/v1/feedback/65a000000000000000000000", {"json": {"helpful": False}, "headers": {"X-Edit-Token": "t"}}),
    ("delete", "/api/v1/feedback/65a000000000000000000000", {"headers": {"X-Edit-Token": "t"}}),
])
def test_every_operation_returns_503_when_not_configured(client, no_store, method, path, kwargs):
    r = getattr(client, method)(path, **kwargs)
    assert r.status_code == 503
    assert r.json()["code"] == "feedback_store_not_configured" and r.headers["retry-after"] == "60"


def test_unreachable_store_returns_503_without_leaking_the_uri(client, monkeypatch, caplog):
    monkeypatch.setattr(settings, "MONGODB_URI", SecretStr("mongodb://u:never-shown-321@127.0.0.1:1/x"))
    mongo.reset_clients()
    try:
        r = client.get("/api/v1/feedback/summary")
    finally:
        mongo.reset_clients()
    assert r.status_code == 503 and r.json()["code"] == "feedback_store_unavailable"
    assert "never-shown-321" not in r.text and "never-shown-321" not in caplog.text


def test_only_a_hash_of_the_edit_token_is_kept():
    token, digest = mongo.new_edit_token()
    assert len(token) >= 32 and token not in digest and len(digest) == 64
    assert mongo.token_matches(token, digest) and not mongo.token_matches(token + "x", digest)


def test_empty_update_is_rejected(client, no_store):
    r = client.patch("/api/v1/feedback/65a000000000000000000000", json={}, headers={"X-Edit-Token": "t"})
    assert r.status_code == 422


# --- against a throwaway MongoDB ---------------------------------------------------------------------------

needs_db = pytest.mark.skipif(not TEST_MONGODB_URI, reason="TEST_MONGODB_URI is not set (CI provides one)")


@pytest.fixture
def store(monkeypatch):
    host = urlparse(TEST_MONGODB_URI).hostname
    if host not in ("localhost", "127.0.0.1") and not urlparse(TEST_MONGODB_URI).path.rstrip("/").endswith("_test"):
        pytest.fail("TEST_MONGODB_URI must point at localhost or a database whose name ends in _test")
    monkeypatch.setattr(settings, "MONGODB_URI", SecretStr(TEST_MONGODB_URI))
    mongo.reset_clients()
    col = mongo.collection()
    col.delete_many({})
    yield col
    col.delete_many({})
    mongo.reset_clients()


@needs_db
def test_full_crud_cycle(client, store):
    # Create: 201, Location header, one-time token; the stored document holds only the hash.
    r = client.post("/api/v1/feedback", json=VALID)
    assert r.status_code == 201
    created = r.json()
    fid, token = created["id"], created["edit_token"]
    assert r.headers["location"] == f"/api/v1/feedback/{fid}"
    stored = store.find_one()
    assert set(stored) == {"_id", "helpful", "section", "model_version", "created_at", "updated_at", "edit_token_hash"}
    assert stored["edit_token_hash"] != token

    # Read: 200, never the token or its hash.
    r = client.get(f"/api/v1/feedback/{fid}")
    assert r.status_code == 200 and r.json()["helpful"] is True
    assert "edit_token" not in r.json() and "edit_token_hash" not in r.json()

    # Update: 200 with the token; updated_at moves on.
    r = client.patch(f"/api/v1/feedback/{fid}", json={"helpful": False}, headers={"X-Edit-Token": token})
    assert r.status_code == 200 and r.json()["helpful"] is False
    assert r.json()["updated_at"] >= created["updated_at"]

    # Delete: 204, then the document is gone (404).
    r = client.delete(f"/api/v1/feedback/{fid}", headers={"X-Edit-Token": token})
    assert r.status_code == 204 and r.content == b""
    assert client.get(f"/api/v1/feedback/{fid}").status_code == 404
    assert store.count_documents({}) == 0


@needs_db
def test_changes_need_the_right_token(client, store):
    fid = client.post("/api/v1/feedback", json=VALID).json()["id"]
    assert client.patch(f"/api/v1/feedback/{fid}", json={"helpful": False}).status_code == 401
    assert client.patch(f"/api/v1/feedback/{fid}", json={"helpful": False},
                        headers={"X-Edit-Token": "wrong"}).status_code == 403
    assert client.delete(f"/api/v1/feedback/{fid}", headers={"X-Edit-Token": "wrong"}).status_code == 403
    assert store.find_one()["helpful"] is True                      # nothing changed


@needs_db
@pytest.mark.parametrize("fid", ["65a000000000000000000000", "not-an-object-id"])
def test_unknown_or_malformed_ids_are_404(client, store, fid):
    assert client.get(f"/api/v1/feedback/{fid}").status_code == 404
    assert client.delete(f"/api/v1/feedback/{fid}", headers={"X-Edit-Token": "t"}).status_code == 404


@needs_db
def test_summary_aggregates_per_section(client, store):
    for helpful, section in [(True, "why"), (False, "why"), (True, "summary")]:
        client.post("/api/v1/feedback", json={**VALID, "helpful": helpful, "section": section})
    body = client.get("/api/v1/feedback/summary").json()
    assert body["total"] == 3
    assert body["sections"] == [{"section": "summary", "total": 1, "helpful": 1},
                                {"section": "why", "total": 2, "helpful": 1}]
