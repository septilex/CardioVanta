"""Mock Google transport, retaining real Authlib state, PKCE, nonce and RSA ID-token validation."""
import json
import time
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.tests.test_workspace_security import account_api, shared_store
from backend.app.api.endpoints import oauth
from backend.app.db.orm import User, OAuthAccount, OAuthFlow


@pytest.fixture
def google(monkeypatch):
    from authlib.integrations.starlette_client import OAuth
    from unittest.mock import AsyncMock
    provider = OAuth().register("google", client_id="synthetic-client", client_secret="synthetic-secret",
                                authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
                                access_token_url="https://oauth2.googleapis.com/token",
                                client_kwargs={"scope": "openid email", "code_challenge_method": "S256"})
    metadata = {"issuer": "https://accounts.google.com", "id_token_signing_alg_values_supported": ["RS256"]}
    monkeypatch.setattr(provider, "load_server_metadata", AsyncMock(return_value=metadata))
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update(kid="test-key", use="sig", alg="RS256")
    monkeypatch.setattr(provider, "fetch_jwk_set", AsyncMock(return_value={"keys": [jwk]}))
    exchange = AsyncMock()
    monkeypatch.setattr(provider, "fetch_access_token", exchange)
    monkeypatch.setattr(oauth, "google_client", lambda: provider)
    return key, exchange


@pytest.mark.parametrize("variant", ["success", "state", "nonce", "issuer", "audience", "signature", "expired", "cancelled", "unverified"])
def test_google_callback_real_claim_validation(account_api, google, variant):
    client, engine = account_api
    key, exchange = google
    response = client.get("/api/v1/auth/google", follow_redirects=False)
    assert response.status_code == 302
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["code_challenge_method"] == ["S256"]
    assert len(query["code_challenge"][0]) > 30
    stamp = int(time.time())
    claims = {"iss": "https://accounts.google.com", "aud": "synthetic-client", "sub": "synthetic-subject",
              "iat": stamp, "exp": stamp+300, "nonce": query["nonce"][0], "email": "google@example.test", "email_verified": True}
    if variant == "nonce": claims["nonce"] = "wrong"
    if variant == "issuer": claims["iss"] = "https://evil.test"
    if variant == "audience": claims["aud"] = "wrong"
    if variant == "expired": claims["exp"] = stamp-600
    if variant == "unverified": claims["email_verified"] = False
    if variant == "signature": key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    exchange.return_value = {"access_token": "synthetic-provider-access", "token_type": "Bearer",
                             "id_token": jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test-key"})}
    state = "wrong" if variant == "state" else query["state"][0]
    suffix = f"?code=synthetic-code&state={state}" if variant != "cancelled" else "?error=access_denied"
    result = client.get("/api/v1/auth/google/callback"+suffix, follow_redirects=False)
    assert result.status_code == 303
    assert ("login=failed" not in result.headers["location"]) == (variant == "success")
    with Session(engine) as db:
        assert len(db.scalars(select(User)).all()) == int(variant == "success")
        assert db.scalar(select(OAuthFlow)) is None
    replay = client.get("/api/v1/auth/google/callback"+suffix, follow_redirects=False)
    assert "login=failed" in replay.headers["location"]
    if variant == "success":
        assert len(exchange.call_args.kwargs["code_verifier"]) >= 43


def test_secure_linking_never_matches_email_implicitly(account_api):
    client, engine = account_api
    from backend.tests.test_workspace_security import register
    register(client, "existing@example.test")
    info = {"sub": "subject-2", "email": "existing@example.test", "email_verified": True}
    with Session(engine) as db:
        with pytest.raises(ValueError): oauth.resolve_account(db, info)
        user = db.scalar(select(User))
        assert oauth.resolve_account(db, info, user.id).id == user.id
        db.commit()
        assert db.scalar(select(OAuthAccount)).user_id == user.id
