"""Persist local OCR text separately from structured proposals."""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"


def upgrade():
    op.add_column("document_extractions", sa.Column("raw_text", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("document_extractions", "raw_text")
