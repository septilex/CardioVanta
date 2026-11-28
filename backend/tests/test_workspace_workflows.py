"""Upload, Stripe signature, cron and WebSocket behavior using synthetic metadata."""
import hashlib
import hmac
import json
import time
import uuid
from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from backend.tests.test_workspace_security import account_api, shared_store, register
from backend.app.api.endpoints import payments, maintenance
from backend.app.db.orm import User, Role, SupportPayment, PaymentEvent, RefreshSession, UploadBatch, now
from backend.app.core.config import settings
from backend.app.services.imports import HEADERS, parse_csv

CSV = (','.join(HEADERS)+'\ncardiovanta-lr13,1.1.1,synthetic,nested_cv,2026-01-01,reports/synthetic_evaluation.md,roc_auc,0.8\n').encode()


def researcher(client, engine):
    response = register(client)
    with Session(engine) as db:
        user = db.scalar(select(User))
        user.roles = [db.get(Role, "researcher")]
        db.commit()
    return {"Authorization": "Bearer "+response.json()["access_token"]}


def research_tables(engine):
    with engine.begin() as db:
        db.execute(text("CREATE TABLE model_versions(id INTEGER PRIMARY KEY, model_id TEXT, version TEXT)"))
        db.execute(text("CREATE TABLE cohorts(id INTEGER PRIMARY KEY, code TEXT)"))
        db.execute(text("CREATE TABLE evaluations(id INTEGER PRIMARY KEY, model_version_id INTEGER, cohort_id INTEGER, method TEXT, evaluated_on DATE, source TEXT, UNIQUE(model_version_id,cohort_id,method))"))
        db.execute(text("CREATE TABLE metrics(evaluation_id INTEGER,metric TEXT,value NUMERIC,PRIMARY KEY(evaluation_id,metric))"))
        db.execute(text("INSERT INTO model_versions VALUES(1,'cardiovanta-lr13','1.1.1')"))
        db.execute(text("INSERT INTO cohorts VALUES(1,'synthetic')"))


@pytest.mark.parametrize("data,name,mime,status", [
    (CSV, "../../escape.csv", "text/csv", 422), (CSV, "data.exe", "text/csv", 422),
    (CSV, "data.csv", "application/pdf", 422), (b"x"*262145, "data.csv", "text/csv", 413),
    (CSV.replace(b"roc_auc,0.8", b"roc_auc,NaN"), "data.csv", "text/csv", 422),
    (CSV.replace(b"metric_value", b"patient_name"), "data.csv", "text/csv", 422),
    (CSV+b"\xff", "data.csv", "text/csv", 422),
    (CSV+CSV.split(b"\n")[1]+b"\n", "data.csv", "text/csv", 409),
    (CSV.replace(b"2026-01-01", b"2099-01-01"), "data.csv", "text/csv", 422),
], ids=["traversal", "extension", "mime", "size", "nan", "clinical-column", "utf8", "duplicate", "future-date"])
def test_csv_security(data, name, mime, status):
    with pytest.raises(HTTPException) as error:
        parse_csv(data, name, mime)
    assert error.value.status_code == status


def test_valid_csv():
    rows = parse_csv(CSV, "metrics.csv", "text/csv")
    assert len(rows) == 1 and rows[0]["metric_name"] == "roc_auc"


def test_upload_auth_and_body_bound(account_api):
    client, engine = account_api
    assert client.post("/api/v1/research/imports").status_code == 401
    token = register(client).json()["access_token"]
    assert client.post("/api/v1/research/imports", headers={"Authorization": "Bearer "+token}).status_code == 403
    assert client.post("/api/v1/auth/login", content=b"x"*65537).status_code == 413


def test_upload_transaction_and_duplicate(account_api, monkeypatch):
    client, engine = account_api
    headers = researcher(client, engine)
    research_tables(engine)
    # SQLite driver cannot bind Decimal to raw text SQL; real PostgreSQL coverage uses Decimal unchanged.
    from backend.app.api.endpoints import imports
    original = imports.parse_csv
    monkeypatch.setattr(imports, "parse_csv", lambda *args: [{**row, "metric_value": float(row["metric_value"])} for row in original(*args)])
    batch = client.post("/api/v1/research/imports", headers=headers).json()
    response = client.post(f"/api/v1/research/imports/{batch['id']}/file", headers=headers, files={"file": ("metrics.csv", CSV, "text/csv")})
    assert response.status_code == 200, response.text
    assert response.json()["row_count"] == 1 and response.json()["status"] == "completed"
    assert client.post(f"/api/v1/research/imports/{batch['id']}/file", headers=headers, files={"file": ("metrics.csv", CSV, "text/csv")}).status_code == 409
    with engine.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM metrics")) == 1
    bad = client.post("/api/v1/research/imports", headers=headers).json()
    response = client.post(f"/api/v1/research/imports/{bad['id']}/file", headers=headers, files={"file": ("metrics.csv", CSV.replace(b"synthetic,", b"unknown,"), "text/csv")})
    assert response.status_code == 422
    assert client.get(f"/api/v1/research/imports/{bad['id']}", headers=headers).json()["status"] == "failed"


def configure_payments(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENTS_ENABLED", True)
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", SecretStr("sk_test_synthetic_only"))
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SecretStr("whsec_synthetic_only"))


def signed_event(event):
    raw = json.dumps(event).encode()
    stamp = int(time.time())
    signature = hmac.new(settings.require_secret("STRIPE_WEBHOOK_SECRET").encode(), str(stamp).encode()+b"."+raw, hashlib.sha256).hexdigest()
    return raw, {"stripe-signature": f"t={stamp},v1={signature}"}


def test_checkout_and_verified_idempotent_webhook(account_api, monkeypatch):
    client, engine = account_api
    configure_payments(monkeypatch)
    monkeypatch.setattr(payments, "create_checkout", lambda item: SimpleNamespace(id="cs_test_synthetic", url="https://checkout.stripe.com/test", livemode=False))
    body = {"amount": 500, "request_key": str(uuid.uuid4())}
    assert client.post("/api/v1/support/checkout", json=body).status_code == 200
    assert client.post("/api/v1/support/checkout", json=body).status_code == 200
    assert client.post("/api/v1/support/checkout", json={**body, "amount": 1000}).status_code == 409
    with Session(engine) as db:
        payment = db.scalar(select(SupportPayment))
        assert payment.status == "pending"  # A checkout redirect is never payment proof.
        reference = str(payment.id)
    event = {"id": "evt_synthetic", "type": "checkout.session.completed", "livemode": False,
             "data": {"object": {"id": "cs_test_synthetic", "client_reference_id": reference, "currency": "usd", "amount_total": 500, "payment_status": "paid"}}}
    raw, headers = signed_event(event)
    assert client.post("/api/v1/support/webhook", content=raw, headers={"stripe-signature": "invalid"}).status_code == 400
    assert client.post("/api/v1/support/webhook", content=raw, headers=headers).status_code == 200
    assert client.post("/api/v1/support/webhook", content=raw, headers=headers).status_code == 200
    with Session(engine) as db:
        assert db.scalar(select(SupportPayment)).status == "paid"
        assert len(db.scalars(select(PaymentEvent)).all()) == 1
    live, headers = signed_event({**event, "livemode": True})
    assert client.post("/api/v1/support/webhook", content=live, headers=headers).status_code == 400
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", SecretStr("sk_live_not_allowed"))
    assert not payments.enabled()


def test_checkout_provider_failure(account_api, monkeypatch):
    client, _ = account_api
    configure_payments(monkeypatch)
    monkeypatch.setattr(payments, "create_checkout", lambda item: (_ for _ in ()).throw(ValueError("provider-secret")))
    result = client.post("/api/v1/support/checkout", json={"amount": 500, "request_key": str(uuid.uuid4())})
    assert result.status_code == 503 and "provider-secret" not in result.text


def test_cron_authorization_cleanup_and_idempotence(account_api, monkeypatch):
    client, engine = account_api
    register(client)
    monkeypatch.setattr(settings, "CRON_SECRET", SecretStr("synthetic-cron-"*4))
    assert client.get("/api/v1/maintenance/daily").status_code == 401
    with Session(engine) as db:
        db.scalar(select(RefreshSession)).expires_at = now()-timedelta(days=1)
        db.commit()
    headers = {"Authorization": "Bearer "+settings.require_secret("CRON_SECRET")}
    assert client.get("/api/v1/maintenance/daily", headers=headers).json()["removed_sessions"] == 1
    assert client.get("/api/v1/maintenance/daily", headers=headers).json()["status"] == "already_completed"
    monkeypatch.setattr(maintenance, "maintain", lambda db: (_ for _ in ()).throw(ValueError("secret")))
    assert client.get("/api/v1/maintenance/daily", headers=headers).status_code == 503


def test_websocket_auth_and_durable_status(account_api, monkeypatch):
    client, engine = account_api
    headers = researcher(client, engine)
    monkeypatch.setattr(settings, "REALTIME_ENABLED", True)
    batch = client.post("/api/v1/research/imports", headers=headers).json()
    path = f"/api/v1/research/imports/{batch['id']}/live"
    with client.websocket_connect(path, headers={"Origin": "http://testserver"}) as socket:
        socket.send_json({"token": headers["Authorization"].split()[1]})
        assert socket.receive_json()["status"] == "ready"
        with Session(engine) as db:
            item = db.get(UploadBatch, uuid.UUID(batch["id"]))
            item.status, item.row_count = "completed", 3
            db.commit()
        assert socket.receive_json()["row_count"] == 3
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(path, headers={"Origin": "https://evil.test"}):
            pass
    with client.websocket_connect(path, headers={"Origin": "http://testserver"}) as socket:
        socket.send_json({"token": "forged"})
        with pytest.raises(WebSocketDisconnect):
            socket.receive_json()
