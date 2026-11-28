import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.auth import security as auth
from backend.app.db.orm import User, Role, RefreshSession, session, now
from backend.app.services.shared import anonymous_id, digest, limit

router = APIRouter()


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=1, max_length=128)


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)


class RoleChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["viewer", "researcher", "admin"]


def attempt(request: Request):
    auth.require_auth()
    auth.check_origin(request)
    limit("auth", anonymous_id(request), 10, 60)


@router.get("/auth/status")
def status():
    from backend.app.core.config import settings
    return {"enabled": auth.enabled(), "google": bool(auth.enabled() and settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)}


@router.post("/auth/register", status_code=201)
def register(body: Credentials, request: Request, response: Response, db: Session = Depends(session)):
    attempt(request)
    hashed = auth.password_hash(body.password)
    user = User(email=body.email.lower().strip(), password_hash=hashed, roles=[db.get(Role, "viewer")])
    try:
        db.add(user)
        db.flush()
        result = auth.new_session(db, user, response)
        db.commit()
        return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Registration could not be completed. Try signing in.") from None


@router.post("/auth/login")
def login(body: Credentials, request: Request, response: Response, db: Session = Depends(session)):
    attempt(request)
    email = body.email.lower().strip()
    limit("account-login", email, 10, 300)
    user = db.scalar(select(User).where(User.email == email))
    valid = auth.password_matches(body.password, user.password_hash if user else None)
    if not valid or not user.active:
        raise HTTPException(401, "Email or password is incorrect.")
    if auth.hasher.check_needs_rehash(user.password_hash):
        user.password_hash = auth.password_hash(body.password)
    result = auth.new_session(db, user, response)
    db.commit()
    return result


@router.post("/auth/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(session)):
    attempt(request)
    raw = request.cookies.get(auth.COOKIE, "")
    item = db.scalar(select(RefreshSession).where(RefreshSession.token_hash == digest(raw)).with_for_update())
    if not item:
        raise HTTPException(401, "Session expired. Sign in again.")
    user = db.scalar(select(User).where(User.id == item.user_id).with_for_update())
    if item.consumed:
        auth.revoke(db, user)
        db.commit()  # Persist replay revocation even though this request returns 401.
        raise HTTPException(401, "Session reuse detected. Sign in again.")
    if item.expires_at.replace(tzinfo=now().tzinfo) <= now() or not user.active:
        raise HTTPException(401, "Session expired. Sign in again.")
    item.consumed = True
    result = auth.new_session(db, user, response, family=item.family)
    db.commit()
    return result


@router.get("/auth/me")
def me(user: User = Depends(auth.current_user)):
    return auth.view(user)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, user: User = Depends(auth.current_user), db: Session = Depends(session)):
    auth.check_origin(request)
    auth.revoke(db, user)
    db.commit()
    response.delete_cookie(auth.COOKIE, path="/api/v1/auth", secure=auth.settings.COOKIE_SECURE, httponly=True, samesite="strict")


@router.post("/auth/password", status_code=204)
def change_password(body: PasswordChange, request: Request, user: User = Depends(auth.current_user), db: Session = Depends(session)):
    auth.check_origin(request)
    limit("password", str(user.id), 5, 300)
    if not auth.password_matches(body.current_password, user.password_hash):
        raise HTTPException(401, "Current password is incorrect.")
    user.password_hash = auth.password_hash(body.new_password)
    auth.revoke(db, user)
    db.commit()


@router.get("/admin/users")
def users(admin: User = Depends(auth.require_roles("admin")), db: Session = Depends(session)):
    return {"users": [auth.view(u) for u in db.scalars(select(User).order_by(User.created_at.desc()).limit(100))]}


@router.patch("/admin/users/{user_id}/role")
def set_role(user_id: uuid.UUID, body: RoleChange, request: Request,
             admin: User = Depends(auth.require_roles("admin")), db: Session = Depends(session)):
    auth.check_origin(request)
    limit("admin", str(admin.id), 20)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Account not found.")
    if user.id == admin.id:
        raise HTTPException(409, "Ask another administrator to change your role.")
    user.roles = [db.get(Role, body.role)]
    auth.revoke(db, user)
    db.commit()
    return auth.view(user)
