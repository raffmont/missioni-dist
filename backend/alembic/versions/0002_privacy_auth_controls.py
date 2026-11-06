"""Privacy lifecycle, persistent throttling and administrator role."""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    op.execute("ALTER TYPE role ADD VALUE IF NOT EXISTS 'ADMIN'")
    op.create_table(
        "login_throttles",
        sa.Column("key_hash", sa.String(64), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("window_started", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "retention_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("cutoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("candidates", sa.Integer(), nullable=False),
        sa.Column("deleted", sa.Integer(), nullable=False),
        sa.Column("verification_hash", sa.String(64), nullable=False),
    )


def downgrade():
    op.drop_table("retention_runs")
    op.drop_table("login_throttles")
