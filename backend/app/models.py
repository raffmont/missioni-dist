import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid.uuid4())


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    REQUESTER = "REQUESTER"
    PROTOCOL_OFFICER = "PROTOCOL_OFFICER"
    MISSIONS_OFFICER = "MISSIONS_OFFICER"


class Status(str, enum.Enum):
    DRAFT = "DRAFT"
    AUTHORIZATION_READY = "AUTHORIZATION_READY"
    AUTHORIZED = "AUTHORIZED"


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(Enum(Role))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship()


class Mission(Base):
    __tablename__ = "missions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    requester_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    destination: Mapped[str] = mapped_column(String(160))
    country: Mapped[str] = mapped_column(String(80), default="Italia")
    purpose: Mapped[str] = mapped_column(Text)
    transport_modes: Mapped[list[str]] = mapped_column(JSON)
    # Kept as a compatibility projection for pre-0.2 API clients.
    transport_mode: Mapped[str] = mapped_column(String(80))
    fund_code: Mapped[str] = mapped_column(String(80))
    cup: Mapped[str | None] = mapped_column(String(40))
    fund_manager: Mapped[str] = mapped_column(String(120))
    planned_start: Mapped[date] = mapped_column(Date)
    planned_end: Mapped[date] = mapped_column(Date)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.DRAFT)
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    authorization: Mapped["Authorization|None"] = relationship(
        back_populates="mission", uselist=False
    )
    __table_args__ = (Index("ix_mission_requester_status", "requester_id", "status"),)


class Authorization(Base):
    __tablename__ = "authorizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("missions.id", ondelete="CASCADE"), unique=True
    )
    protocol_number: Mapped[str | None] = mapped_column(String(80))
    protocol_date: Mapped[date | None] = mapped_column(Date)
    rendered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    document_version: Mapped[int] = mapped_column(default=0)
    mission: Mapped[Mission] = relationship(back_populates="authorization")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    mission_id: Mapped[str | None] = mapped_column(
        ForeignKey("missions.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(80))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    metadata_redacted: Mapped[str] = mapped_column(String(200), default="{}")


class LoginThrottle(Base):
    __tablename__ = "login_throttles"
    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(default=0)
    window_started: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RetentionRun(Base):
    __tablename__ = "retention_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    dry_run: Mapped[bool] = mapped_column(default=True)
    candidates: Mapped[int] = mapped_column(default=0)
    deleted: Mapped[int] = mapped_column(default=0)
    verification_hash: Mapped[str] = mapped_column(String(64), default="")
