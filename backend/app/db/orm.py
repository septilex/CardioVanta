"""SQLAlchemy 2 mapped accounts/operations. Schema changes use versioned SQL migrations."""
import uuid
from datetime import date, datetime, timezone
from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
from sqlalchemy.pool import NullPool

from backend.app.core.config import settings, MissingSecretError


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_name: Mapped[str] = mapped_column(ForeignKey("roles.name"), primary_key=True)


class Role(Base):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(20), primary_key=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    roles: Mapped[list[Role]] = relationship(secondary="user_roles", lazy="selectin")


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    __table_args__ = (UniqueConstraint("provider", "subject"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(30))
    subject: Mapped[str] = mapped_column(String(255))


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    family: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)


class UploadBatch(Base):
    __tablename__ = "upload_batches"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="ready")
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class OAuthFlow(Base):
    __tablename__ = "oauth_flows"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[str] = mapped_column(Text)
    link_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SupportPayment(Base):
    __tablename__ = "support_payments"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    request_key: Mapped[str] = mapped_column(String(64), unique=True)
    amount: Mapped[int] = mapped_column(Integer)
    checkout_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PaymentEvent(Base):
    __tablename__ = "payment_events"
    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("support_payments.id"))
    event_type: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MaintenanceRun(Base):
    __tablename__ = "maintenance_runs"
    run_date: Mapped[date] = mapped_column(Date, primary_key=True)
    removed_sessions: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


@lru_cache(maxsize=4)
def engine(url: str):
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url, poolclass=NullPool, connect_args={"connect_timeout": 5}, hide_parameters=True)


def session():
    try:
        with Session(engine(settings.require_secret("DATABASE_URL")), expire_on_commit=False) as db:
            yield db
    except (MissingSecretError, SQLAlchemyError):
        raise HTTPException(503, "Research account database is unavailable.") from None
