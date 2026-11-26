"""
Research evaluations in PostgreSQL (openspec/changes/research-evaluations-postgres).

Always run: the endpoint's 503 paths (not configured, unreachable), and static checks of the SQL.
With TEST_DATABASE_URL (a throwaway PostgreSQL; CI provides a service container): the migrations, the
foreign keys and the three JOIN queries, end to end through the API. Research metadata only, no patient data.
"""
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from backend.app.core.config import Settings, settings
from backend.app.db import research
from backend.app.db.migrate import SQL_DIR, apply_migrations, migration_files
from backend.app.db.postgres import ResearchDatabaseUnavailable, connect
from backend.app.main import app

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "").strip()
TABLES = ("metrics", "evaluations", "cohorts", "model_versions", "schema_migrations")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# --- no database needed ------------------------------------------------------------------------------------

def test_not_configured_returns_503_and_predictions_still_work(client, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", None)
    r = client.get("/api/v1/research/evaluations")
    assert r.status_code == 503
    assert r.json() == {"detail": "The research database is not configured.", "code": "research_database_not_configured"}
    assert r.headers["cache-control"] == "no-store" and r.headers["retry-after"] == "60"
    assert client.get("/api/v1/health").status_code == 200


def test_unreachable_database_returns_503_without_leaking_the_url(client, monkeypatch, caplog):
    password = "never-printed-789"
    monkeypatch.setattr(settings, "DATABASE_URL", SecretStr(f"postgresql://u:{password}@127.0.0.1:1/x"))
    r = client.get("/api/v1/research/evaluations")
    assert r.status_code == 503 and r.json()["code"] == "research_database_unavailable"
    assert password not in r.text and password not in caplog.text


def test_connect_error_message_never_contains_the_connection_string():
    cfg = Settings(_env_file=None, DATABASE_URL="postgresql://u:secret-pw-000@127.0.0.1:1/x")
    with pytest.raises(ResearchDatabaseUnavailable) as exc:
        with connect(cfg):
            pass
    assert "secret-pw-000" not in str(exc.value) and exc.value.__cause__ is None


def test_queries_are_static_joins():
    assert re.search(r"FROM metrics m\s+JOIN evaluations e .*JOIN model_versions mv .*JOIN cohorts c",
                     research.EVALUATION_TABLE_SQL, re.S)
    assert research.VERSION_COVERAGE_SQL.count("LEFT JOIN") == 2 and "GROUP BY" in research.VERSION_COVERAGE_SQL
    assert "LEFT JOIN evaluations" in research.UNEVALUATED_COHORTS_SQL and "IS NULL" in research.UNEVALUATED_COHORTS_SQL
    for sql in (research.EVALUATION_TABLE_SQL, research.VERSION_COVERAGE_SQL, research.UNEVALUATED_COHORTS_SQL):
        assert "%s" not in sql and "{" not in sql.replace("'{}'", "")   # no interpolation of any kind


def test_schema_declares_the_relationships():
    schema = (SQL_DIR / "001_research_schema.sql").read_text(encoding="utf-8")
    assert "REFERENCES model_versions (id)" in schema and "REFERENCES cohorts (id)" in schema
    assert "REFERENCES evaluations (id) ON DELETE CASCADE" in schema
    assert [p.name for p in migration_files()] == ["001_research_schema.sql", "002_research_seed.sql"]


def test_no_patient_data_columns():
    sql = " ".join(p.read_text(encoding="utf-8").lower() for p in migration_files())
    for clinical in ("age", "chol", "trestbps", "thalach", "probability", "patient_id"):
        assert not re.search(rf"\b{clinical}\b", sql), clinical


# --- against a throwaway PostgreSQL ------------------------------------------------------------------------

def _is_throwaway(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.hostname in ("localhost", "127.0.0.1") or (parsed.path or "").rstrip("/").endswith("_test")


needs_db = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL is not set (CI provides one)")


@pytest.fixture(scope="module")
def db_settings():
    if not _is_throwaway(TEST_DATABASE_URL):
        pytest.fail("TEST_DATABASE_URL must point at localhost or a database whose name ends in _test")
    cfg = Settings(_env_file=None, DATABASE_URL=TEST_DATABASE_URL)
    with connect(cfg, read_only=False) as conn:
        with conn.transaction():
            for table in TABLES:
                conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    return cfg


@needs_db
def test_migrations_apply_once(db_settings):
    assert apply_migrations(db_settings) == ["001_research_schema.sql", "002_research_seed.sql"]
    assert apply_migrations(db_settings) == []


@needs_db
def test_inner_join_returns_each_metric_with_its_version_and_cohort(db_settings):
    rows = research.research_evaluations(db_settings)["evaluations"]
    assert len(rows) == 12
    pick = {(r["version"], r["cohort"], r["metric"]): r for r in rows}
    assert pick[("1.1.0", "cleveland_dev", "calibration_slope")]["value"] == pytest.approx(1.003)
    assert pick[("1.0.0", "cleveland_dev", "calibration_slope")]["value"] == pytest.approx(1.267)
    locked = pick[("1.0.0", "cleveland_locked", "accuracy")]
    assert locked["value"] == pytest.approx(0.852459) and locked["n_patients"] == 61
    assert locked["source"] == "reports/phase2c_final_evaluation.json"


@needs_db
def test_left_join_keeps_versions_without_evaluations(db_settings):
    coverage = {r["version"]: r for r in research.research_evaluations(db_settings)["version_coverage"]}
    assert coverage["1.0.0"]["evaluation_count"] == 2
    assert coverage["1.0.0"]["cohorts"] == ["cleveland_dev", "cleveland_locked"]
    assert coverage["1.1.1"]["evaluation_count"] == 0 and coverage["1.1.1"]["cohorts"] == []


@needs_db
def test_anti_join_lists_cohorts_never_evaluated(db_settings):
    codes = [r["code"] for r in research.research_evaluations(db_settings)["unevaluated_cohorts"]]
    assert codes == ["hungary", "long_beach_va"]


@needs_db
def test_foreign_keys_reject_orphan_rows(db_settings):
    import psycopg

    with connect(db_settings, read_only=False) as conn:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with conn.transaction():
                conn.execute("INSERT INTO evaluations (model_version_id, cohort_id, method, evaluated_on, source) "
                             "VALUES (9999, 9999, 'orphan', '2026-01-01', 'none')")


@needs_db
def test_read_only_connection_refuses_writes(db_settings):
    import psycopg

    with connect(db_settings) as conn:
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            conn.execute("DELETE FROM metrics")


@needs_db
def test_endpoint_returns_the_join_results(client, db_settings, monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", SecretStr(TEST_DATABASE_URL))
    r = client.get("/api/v1/research/evaluations")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"evaluations", "version_coverage", "unevaluated_cohorts"}
    assert len(body["evaluations"]) == 12 and len(body["unevaluated_cohorts"]) == 2
    assert r.headers["cache-control"] == "public, max-age=300"
