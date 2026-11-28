import secrets
import time
import uuid
from datetime import timedelta

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.orm import User, RefreshSession, session, now
from backend.app.services.shared import digest

hasher = PasswordHasher(type=Type.ID, time_cost=3, memory_cost=65536, parallelism=2)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(24))
COOKIE = "cv_refresh"


def enabled():
    return bool(settings.AUTH_ENABLED and settings.DATABASE_URL and settings.REDIS_URL and
                settings.JWT_SIGNING_KEY and len(settings.JWT_SIGNING_KEY.get_secret_value()) >= 32 and
                (settings.ENVIRONMENT == "development" or
                 (settings.COOKIE_SECURE and settings.APP_ORIGIN.startswith("https://"))))


def require_auth():
    if not enabled():
        raise HTTPException(503, "Accounts are not configured.")


def check_origin(request: Request):
    # Cookie-authenticated operations require exact Origin; also prevents login CSRF.
    if request.headers.get("origin") != settings.APP_ORIGIN.rstrip("/"):
        raise HTTPException(403, "Request origin is not allowed.")


def password_hash(password: str):
    if not 12 <= len(password) <= 128 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise HTTPException(422, "Use 12–128 characters including a letter and a number.")
    return hasher.hash(password)


def password_matches(password: str, hashed: str | None):
    try:
        return hasher.verify(hashed or DUMMY_HASH, password) and hashed is not None
    except (VerificationError, InvalidHashError):
        return False


def issue_access(user: User):
    stamp = int(time.time())
    return jwt.encode({"sub": str(user.id), "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE,
                       "iat": stamp, "nbf": stamp, "exp": stamp + min(900, max(60, settings.ACCESS_TOKEN_SECONDS)),
                       "jti": str(uuid.uuid4()), "ver": user.token_version},
                      settings.require_secret("JWT_SIGNING_KEY"), algorithm="HS256")


def verify_access(token: str):
    try:
        claims = jwt.decode(token, settings.require_secret("JWT_SIGNING_KEY"), algorithms=["HS256"],
                            issuer=settings.JWT_ISSUER, audience=settings.JWT_AUDIENCE,
                            options={"require": ["sub", "iss", "aud", "iat", "nbf", "exp", "jti", "ver"]})
        uuid.UUID(claims["sub"])
        uuid.UUID(claims["jti"])
        if type(claims["ver"]) is not int or claims["exp"] - claims["iat"] > 900:
            raise ValueError()
        return claims
    except Exception:
        raise HTTPException(401, "Invalid or expired session.", headers={"WWW-Authenticate": "Bearer"}) from None


def user_for_token(token: str, db: Session):
    claims = verify_access(token)
    user = db.get(User, uuid.UUID(claims["sub"]))
    if not user or not user.active or user.token_version != claims["ver"]:
        raise HTTPException(401, "Invalid or expired session.")
    return user


def current_user(request: Request, db: Session = Depends(session)):
    require_auth()
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Sign in to continue.", headers={"WWW-Authenticate": "Bearer"})
    return user_for_token(token, db)


def require_roles(*allowed: str):
    def dependency(user: User = Depends(current_user)):
        if not {r.name for r in user.roles}.intersection(allowed):
            raise HTTPException(403, "Your role does not permit this operation.")
        return user
    return dependency


def view(user: User):
    return {"id": str(user.id), "email": user.email, "roles": sorted(r.name for r in user.roles)}


def new_session(db: Session, user: User, response: Response, family=None):
    raw = secrets.token_urlsafe(48)
    seconds = min(2592000, max(3600, settings.REFRESH_TOKEN_SECONDS))
    db.add(RefreshSession(user_id=user.id, family=family or uuid.uuid4(), token_hash=digest(raw),
                          expires_at=now()+timedelta(seconds=seconds)))
    response.set_cookie(COOKIE, raw, max_age=seconds, httponly=True, secure=settings.COOKIE_SECURE,
                        samesite="strict", path="/api/v1/auth")
    response.headers["Cache-Control"] = "no-store"
    return {"access_token": issue_access(user), "token_type": "bearer", "user": view(user)}


def revoke(db: Session, user: User):
    user.token_version += 1
    db.execute(update(RefreshSession).where(RefreshSession.user_id == user.id).values(consumed=True))
