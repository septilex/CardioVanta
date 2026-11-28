"""Authlib OIDC: state, nonce and S256 PKCE; one-use server-side authorization sessions."""
import json
import secrets
from datetime import timedelta

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from backend.app.auth import security as auth
from backend.app.core.config import settings
from backend.app.db.orm import OAuthFlow, OAuthAccount, User, Role, session, now
from backend.app.services.shared import anonymous_id, digest, limit

router = APIRouter()
FLOW_COOKIE = "cv_oauth"


def google_client():
    auth.require_auth()
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(503, "Google sign-in is not configured.")
    oauth = OAuth()
    return oauth.register("google", client_id=settings.GOOGLE_CLIENT_ID,
                          client_secret=settings.require_secret("GOOGLE_CLIENT_SECRET"),
                          server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                          client_kwargs={"scope": "openid email", "code_challenge_method": "S256", "timeout": 10})


async def start(request: Request, db: Session, link_user=None):
    client = google_client()
    await run_in_threadpool(limit, "oauth", anonymous_id(request), 10)
    request.scope["session"] = {}
    response = await client.authorize_redirect(request, settings.APP_ORIGIN.rstrip("/")+"/api/v1/auth/google/callback")
    token = secrets.token_urlsafe(32)
    db.add(OAuthFlow(token_hash=digest(token), payload=json.dumps(request.session),
                     link_user_id=link_user.id if link_user else None, expires_at=now()+timedelta(minutes=5)))
    db.commit()
    if link_user:
        response = JSONResponse({"url": response.headers["location"]})
    response.set_cookie(FLOW_COOKIE, token, httponly=True, secure=settings.COOKIE_SECURE,
                        samesite="lax", max_age=300, path="/api/v1/auth/google")
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/auth/google")
async def login(request: Request, db: Session = Depends(session)):
    return await start(request, db)


@router.post("/auth/google/link")
async def link(request: Request, user: User = Depends(auth.current_user), db: Session = Depends(session)):
    auth.check_origin(request)
    return await start(request, db, user)


def resolve_account(db: Session, info, link_user_id=None):
    # A verified email is never sufficient to silently link an existing password account.
    if not info.get("sub") or info.get("email_verified") is not True or not info.get("email"):
        raise ValueError("Unverified identity")
    mapping = db.scalar(select(OAuthAccount).where(OAuthAccount.provider == "google", OAuthAccount.subject == info["sub"]))
    if mapping:
        if link_user_id and mapping.user_id != link_user_id:
            raise ValueError("Identity already linked")
        return db.get(User, mapping.user_id)
    email = info["email"].lower()
    user = db.get(User, link_user_id) if link_user_id else db.scalar(select(User).where(User.email == email))
    if user and not link_user_id:
        raise ValueError("Explicit authenticated linking required")
    if link_user_id and (not user or not user.active or user.email != email):
        raise ValueError("Account link mismatch")
    if not user:
        user = User(email=email, roles=[db.get(Role, "viewer")])
        db.add(user)
        db.flush()
    db.add(OAuthAccount(user_id=user.id, provider="google", subject=info["sub"]))
    return user


@router.get("/auth/google/callback")
async def callback(request: Request, db: Session = Depends(session)):
    client = google_client()
    # DELETE RETURNING atomically consumes the flow before external I/O; replay cannot exchange twice.
    flow = db.execute(delete(OAuthFlow).where(OAuthFlow.token_hash == digest(request.cookies.get(FLOW_COOKIE, "")))
                      .returning(OAuthFlow.payload, OAuthFlow.link_user_id, OAuthFlow.expires_at)).first()
    db.commit()
    response = RedirectResponse(settings.APP_ORIGIN.rstrip("/")+"/research/workspace?login=failed", status_code=303)
    try:
        if not flow or flow.expires_at.replace(tzinfo=now().tzinfo) <= now():
            raise ValueError("Expired flow")
        request.scope["session"] = json.loads(flow.payload)
        token = await client.authorize_access_token(request)  # Authlib verifies state, JWKS, iss/aud/exp, nonce.
        user = resolve_account(db, token["userinfo"], flow.link_user_id)
        if not user.active:
            raise ValueError("Inactive user")
        response = RedirectResponse(settings.APP_ORIGIN.rstrip("/")+"/research/workspace", status_code=303)
        auth.new_session(db, user, response)
        db.commit()
    except Exception:
        db.rollback()
    response.delete_cookie(FLOW_COOKIE, path="/api/v1/auth/google")
    response.headers["Cache-Control"] = "no-store"
    return response
