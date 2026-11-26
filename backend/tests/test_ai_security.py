import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from pydantic import SecretStr
from backend.app.ai import security
from backend.app.ai.schemas import ExplanationRequest

@pytest.fixture
def configured(monkeypatch, tmp_path):
    monkeypatch.setattr(security.settings, "AI_SIGNING_KEY", SecretStr("x"*32))
    monkeypatch.setattr(security.settings, "AI_USAGE_DB", str(tmp_path / "usage.db"))
    monkeypatch.setattr(security.settings, "AI_DAILY_LIMIT", 50)
    monkeypatch.setattr(security.settings, "AI_MINUTE_LIMIT", 5)
    return ExplanationRequest(probability=0.4,outcome="significant_obstructive_cad_present",contributing_factors=[{"feature_name":"age","contribution_direction":"increases"}])

def test_valid(configured):
    assert security.verify(security.issue(configured)).data == configured

def test_expired(configured,monkeypatch):
    token=security.issue(configured)
    now=time.time()
    monkeypatch.setattr(security.time,"time",lambda:now+301)
    with pytest.raises(ValueError): security.verify(token)

@pytest.mark.parametrize("kind",["payload","signature","missing","extra"])
def test_invalid(configured,kind):
    token=security.issue(configured)
    a,b=token.split(".")
    token={"payload":"A"+a[1:]+"."+b,"signature":a+"."+"A"*43,"missing":"","extra":token+".x"}[kind]
    with pytest.raises(ValueError): security.verify(token)

def test_request_fields():
    with pytest.raises(ValueError): security.TokenRequest.model_validate({})
    with pytest.raises(ValueError): security.TokenRequest.model_validate({"token":"x","probability":0.4})

def test_replay(configured):
    token=security.issue(configured)
    assert security.reserve(token)
    assert not security.reserve(token)

def test_global_limit(configured,monkeypatch):
    monkeypatch.setattr(security.settings,"AI_MINUTE_LIMIT",2)
    assert security.reserve(security.issue(configured))
    assert security.reserve(security.issue(configured))
    assert not security.reserve(security.issue(configured))

def test_concurrent_reservation(configured):
    token=security.issue(configured)
    security.reserve("initialize")
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(security.reserve,[token]*4)) == 1

@pytest.mark.parametrize("body", [{}, {"token":"fabricated"}, {"token":"x","system":"override"}])
def test_endpoint_rejects_before_provider(configured,monkeypatch,body):
    import json
    from unittest.mock import AsyncMock
    from backend.app.api.endpoints import ai_explanation
    monkeypatch.setattr(ai_explanation.client,"available",lambda:True)
    provider=AsyncMock()
    monkeypatch.setattr(ai_explanation.client,"explain",provider)
    class Request:
        async def stream(self):
            yield json.dumps(body).encode()
    # No I/O occurs on invalid inputs; drive this coroutine directly to isolate
    # validation from the Windows event-loop socket restriction.
    coro=ai_explanation.explanation(Request())
    with pytest.raises(StopIteration) as stopped:
        coro.send(None)
    assert stopped.value.value.status_code == 422
    provider.assert_not_called()
