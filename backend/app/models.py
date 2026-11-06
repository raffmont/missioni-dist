import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
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


class DocumentStatus(str, enum.Enum):
    UPLOADING = "UPLOADING"
    STORED = "STORED"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"


class ExpenseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    VERIFIED = "VERIFIED"
    EXCLUDED = "EXCLUDED"


class AllocationStatus(str, enum.Enum):
    SUGGESTED = "SUGGESTED"
    CONFIRMED = "CONFIRMED"
    REVOKED = "REVOKED"


class ReceiptDocument(Base):
    __tablename__ = "receipt_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("missions.id", ondelete="CASCADE"), index=True
    )
    expense_id: Mapped[str | None] = mapped_column(
        ForeignKey("expenses.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.UPLOADING
    )
    object_key: Mapped[str] = mapped_column(String(255), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(80))
    size_bytes: Mapped[int] = mapped_column()
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    page_count: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        UniqueConstraint("owner_id", "mission_id", "sha256", name="uq_document_upload"),
    )


class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("missions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[ExpenseStatus] = mapped_column(Enum(ExpenseStatus), default=ExpenseStatus.DRAFT)
    expense_date: Mapped[date | None] = mapped_column(Date)
    merchant: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(80))
    document_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    personally_paid: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    reimbursement_claimed: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    eur_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    conversion_criterion: Mapped[str | None] = mapped_column(String(240))
    notes: Mapped[str | None] = mapped_column(Text)
    confirmed_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("receipt_documents.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(40))
    provider_version: Mapped[str] = mapped_column(String(40))
    raw_text: Mapped[str | None] = mapped_column(Text)
    proposed_fields: Mapped[dict] = mapped_column(JSON)
    confidences: Mapped[dict] = mapped_column(JSON)
    provenance: Mapped[dict] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BankImport(Base):
    __tablename__ = "bank_imports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    mission_id: Mapped[str] = mapped_column(
        ForeignKey("missions.id", ondelete="CASCADE"), index=True
    )
    file_sha256: Mapped[str] = mapped_column(String(64))
    institution: Mapped[str | None] = mapped_column(String(120))
    account_reference_masked: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        UniqueConstraint("owner_id", "mission_id", "file_sha256", name="uq_bank_import"),
    )


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    import_id: Mapped[str] = mapped_column(
        ForeignKey("bank_imports.id", ondelete="CASCADE"), index=True
    )
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    operation_date: Mapped[date] = mapped_column(Date)
    booking_date: Mapped[date | None] = mapped_column(Date)
    full_description: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3))
    source_account: Mapped[str | None] = mapped_column(String(80))
    external_reference: Mapped[str | None] = mapped_column(String(160))
    selected: Mapped[bool] = mapped_column(default=False)


class ExpenseAllocation(Base):
    __tablename__ = "expense_allocations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("bank_transactions.id", ondelete="CASCADE"), index=True
    )
    expense_id: Mapped[str] = mapped_column(
        ForeignKey("expenses.id", ondelete="CASCADE"), index=True
    )
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    status: Mapped[AllocationStatus] = mapped_column(Enum(AllocationStatus))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    rationale: Mapped[str | None] = mapped_column(String(240))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
