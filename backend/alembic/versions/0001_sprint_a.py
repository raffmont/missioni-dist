"""Sprint A schema."""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column(
            "role",
            sa.Enum("REQUESTER", "PROTOCOL_OFFICER", "MISSIONS_OFFICER", name="role"),
            nullable=False,
        ),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_table(
        "missions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "requester_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("destination", sa.String(160), nullable=False),
        sa.Column("country", sa.String(80), nullable=False),
        sa.Column("purpose", sa.Text, nullable=False),
        sa.Column("transport_mode", sa.String(80), nullable=False),
        sa.Column("fund_code", sa.String(80), nullable=False),
        sa.Column("cup", sa.String(40)),
        sa.Column("fund_manager", sa.String(120), nullable=False),
        sa.Column("planned_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planned_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "AUTHORIZATION_READY", "AUTHORIZED", name="status"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_missions_requester_id", "missions", ["requester_id"])
    op.create_index("ix_mission_requester_status", "missions", ["requester_id", "status"])
    op.create_table(
        "authorizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "mission_id",
            sa.String(36),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("protocol_number", sa.String(80)),
        sa.Column("protocol_date", sa.Date),
        sa.Column("rendered_at", sa.DateTime(timezone=True)),
        sa.Column("document_version", sa.Integer, nullable=False),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "actor_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("mission_id", sa.String(36), sa.ForeignKey("missions.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_redacted", sa.String(200), nullable=False),
    )
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_mission_id", "audit_events", ["mission_id"])


def downgrade():
    for table in ["audit_events", "authorizations", "missions", "sessions", "users"]:
        op.drop_table(table)
