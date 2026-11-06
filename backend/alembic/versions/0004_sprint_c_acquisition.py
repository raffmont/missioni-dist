"""Sprint C document-first acquisition and bank reconciliation.

Additive migration: existing Sprint A records and workflow are unchanged.
"""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade():
    document_status = sa.Enum(
        "UPLOADING", "STORED", "PROCESSING", "EXTRACTED", "EXTRACTION_FAILED", name="documentstatus"
    )
    expense_status = sa.Enum("DRAFT", "NEEDS_REVIEW", "VERIFIED", "EXCLUDED", name="expensestatus")
    allocation_status = sa.Enum("SUGGESTED", "CONFIRMED", "REVOKED", name="allocationstatus")
    op.create_table(
        "expenses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "mission_id",
            sa.String(36),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", expense_status, nullable=False),
        sa.Column("expense_date", sa.Date),
        sa.Column("merchant", sa.String(200)),
        sa.Column("description", sa.Text),
        sa.Column("category", sa.String(80)),
        sa.Column("document_total", sa.Numeric(14, 2)),
        sa.Column("currency", sa.String(3)),
        sa.Column("personally_paid", sa.Numeric(14, 2)),
        sa.Column("reimbursement_claimed", sa.Numeric(14, 2)),
        sa.Column("eur_amount", sa.Numeric(14, 2)),
        sa.Column("conversion_criterion", sa.String(240)),
        sa.Column("notes", sa.Text),
        sa.Column("confirmed_fields", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_expenses_owner_id", "expenses", ["owner_id"])
    op.create_index("ix_expenses_mission_id", "expenses", ["mission_id"])
    op.create_table(
        "receipt_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "mission_id",
            sa.String(36),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expense_id", sa.String(36), sa.ForeignKey("expenses.id", ondelete="SET NULL")),
        sa.Column("status", document_status, nullable=False),
        sa.Column("object_key", sa.String(255), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("media_type", sa.String(80), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("page_count", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "mission_id", "sha256", name="uq_document_upload"),
    )
    for name, cols in (
        ("ix_receipt_documents_owner_id", ["owner_id"]),
        ("ix_receipt_documents_mission_id", ["mission_id"]),
        ("ix_receipt_documents_expense_id", ["expense_id"]),
        ("ix_receipt_documents_sha256", ["sha256"]),
    ):
        op.create_index(name, "receipt_documents", cols)
    op.create_table(
        "document_extractions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("receipt_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("provider_version", sa.String(40), nullable=False),
        sa.Column("proposed_fields", sa.JSON, nullable=False),
        sa.Column("confidences", sa.JSON, nullable=False),
        sa.Column("provenance", sa.JSON, nullable=False),
        sa.Column("error_code", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_document_extractions_document_id", "document_extractions", ["document_id"])
    op.create_table(
        "bank_imports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "mission_id",
            sa.String(36),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("institution", sa.String(120)),
        sa.Column("account_reference_masked", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "mission_id", "file_sha256", name="uq_bank_import"),
    )
    op.create_index("ix_bank_imports_owner_id", "bank_imports", ["owner_id"])
    op.create_index("ix_bank_imports_mission_id", "bank_imports", ["mission_id"])
    op.create_table(
        "bank_transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "import_id",
            sa.String(36),
            sa.ForeignKey("bank_imports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("operation_date", sa.Date, nullable=False),
        sa.Column("booking_date", sa.Date),
        sa.Column("full_description", sa.Text, nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("source_account", sa.String(80)),
        sa.Column("external_reference", sa.String(160)),
        sa.Column("selected", sa.Boolean, nullable=False),
    )
    op.create_index("ix_bank_transactions_import_id", "bank_transactions", ["import_id"])
    op.create_index("ix_bank_transactions_owner_id", "bank_transactions", ["owner_id"])
    op.create_table(
        "expense_allocations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            sa.String(36),
            sa.ForeignKey("bank_transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "expense_id",
            sa.String(36),
            sa.ForeignKey("expenses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("allocated_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", allocation_status, nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4)),
        sa.Column("rationale", sa.String(240)),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_expense_allocations_owner_id", "expense_allocations", ["owner_id"])
    op.create_index(
        "ix_expense_allocations_transaction_id", "expense_allocations", ["transaction_id"]
    )
    op.create_index("ix_expense_allocations_expense_id", "expense_allocations", ["expense_id"])


def downgrade():
    for table in (
        "expense_allocations",
        "bank_transactions",
        "bank_imports",
        "document_extractions",
        "receipt_documents",
        "expenses",
    ):
        op.drop_table(table)
    for name in ("allocationstatus", "expensestatus", "documentstatus"):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
