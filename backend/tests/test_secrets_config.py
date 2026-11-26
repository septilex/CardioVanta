"""
Environment variables and secrets (backend/app/core/config.py).

Proves that secret settings are read from the environment, masked everywhere they could leak (repr, str,
model_dump, JSON, logs, the configuration check), readable only through require_secret(), optional for
prediction serving, documented by name only in .env.example, kept out of Git and out of the browser bundle.
Uses fake values only.
"""
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

from backend.app.core.config import SECRET_SETTINGS, MissingSecretError, Settings

ROOT = Path(__file__).resolve().parents[2]
FAKE_DB = "postgresql://viva_user:not-a-real-password-123@db.example.invalid:5432/cardiovanta"
FAKE_MONGO = "mongodb+srv://viva_user:also-not-real-456@cluster.example.invalid/cardiovanta"


def _settings(monkeypatch, **env):
    for name in SECRET_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return Settings(_env_file=None)


def test_secrets_are_read_from_the_environment_but_masked_everywhere(monkeypatch, caplog):
    s = _settings(monkeypatch, DATABASE_URL=FAKE_DB, MONGODB_URI=FAKE_MONGO)
    leaks = [repr(s), str(s), str(s.model_dump()), s.model_dump_json(), repr(s.DATABASE_URL), str(s.MONGODB_URI)]
    with caplog.at_level(logging.INFO):
        logging.getLogger("viva").info("settings loaded: %s", s)
    leaks.append(caplog.text)
    for text in leaks:
        assert "not-a-real-password" not in text and "also-not-real" not in text
    assert "**********" in repr(s.DATABASE_URL)


def test_require_secret_is_the_only_way_to_the_value(monkeypatch):
    s = _settings(monkeypatch, DATABASE_URL=FAKE_DB)
    assert s.require_secret("DATABASE_URL") == FAKE_DB
    with pytest.raises(KeyError):
        s.require_secret("MODEL_ID")          # not a secret: read it as a normal attribute


def test_missing_secret_error_names_the_variable_not_a_value(monkeypatch):
    s = _settings(monkeypatch, DATABASE_URL=FAKE_DB)
    with pytest.raises(MissingSecretError, match="MONGODB_URI is not configured") as exc:
        s.require_secret("MONGODB_URI")
    assert "not-a-real-password" not in str(exc.value)


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_value_copied_from_env_example_means_not_configured(monkeypatch, blank):
    s = _settings(monkeypatch, DATABASE_URL=blank)
    assert s.DATABASE_URL is None
    with pytest.raises(MissingSecretError):
        s.require_secret("DATABASE_URL")


def test_prediction_serving_starts_without_any_secret(monkeypatch):
    s = _settings(monkeypatch)
    assert all(getattr(s, name) is None for name in SECRET_SETTINGS)
    assert s.MODEL_ID and s.MODEL_VERSION


def test_configuration_report_shows_presence_only(monkeypatch):
    report = _settings(monkeypatch, DATABASE_URL=FAKE_DB).configuration_report()
    assert report["DATABASE_URL"] == "set" and report["MONGODB_URI"] == "not set"
    assert "not-a-real-password" not in json.dumps(report)


def test_configuration_check_command_never_prints_a_secret():
    env = {k: v for k, v in os.environ.items() if k not in SECRET_SETTINGS}
    env.update(DATABASE_URL=FAKE_DB, MONGODB_URI=FAKE_MONGO, PYTHONPATH=str(ROOT))
    r = subprocess.run([sys.executable, "-m", "backend.app.core.config"], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    lines = dict(line.split(None, 1) for line in r.stdout.splitlines() if line.strip())
    assert lines["DATABASE_URL"].strip() == "set" and lines["MONGODB_URI"].strip() == "set"
    assert "not-a-real-password" not in r.stdout + r.stderr and "also-not-real" not in r.stdout + r.stderr


def test_env_example_lists_secret_names_with_empty_values():
    entries = {}
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            entries[key.strip()] = value.strip()
    for name in SECRET_SETTINGS:
        assert entries.get(name) == "", f"{name} must be listed in .env.example with an empty value"
    assert not [k for k in entries if k.startswith("NEXT_PUBLIC_") and any(s in k for s in SECRET_SETTINGS)]


def test_real_env_files_are_ignored_by_git():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in ignore and ".env.*" in ignore and "!.env.example" in ignore
    try:
        tracked = subprocess.run(["git", "ls-files", ".env", ".env.local", ".env.production"], cwd=ROOT,
                                 capture_output=True, text=True, timeout=30).stdout.split()
    except OSError:
        pytest.skip("git is not available")
    assert tracked == []


def test_secrets_never_reach_the_browser_bundle():
    for path in (ROOT / "src").rglob("*"):
        if path.suffix in (".ts", ".tsx", ".js", ".jsx"):
            text = path.read_text(encoding="utf-8")
            for name in SECRET_SETTINGS:
                assert name not in text, f"{path.relative_to(ROOT)} references {name}"
