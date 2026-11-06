"""Multiple transport modes and date-only mission period."""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade():
    op.add_column("missions", sa.Column("transport_modes", sa.JSON(), nullable=True))
    # Preserve every legacy value exactly; the old projection remains available.
    op.execute("UPDATE missions SET transport_modes = json_build_array(transport_mode)")
    op.alter_column("missions", "transport_modes", nullable=False)
    op.alter_column(
        "missions",
        "planned_start",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.Date(),
        existing_nullable=False,
        postgresql_using="planned_start::date",
    )
    op.alter_column(
        "missions",
        "planned_end",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.Date(),
        existing_nullable=False,
        postgresql_using="planned_end::date",
    )


def downgrade():
    op.alter_column(
        "missions",
        "planned_start",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="planned_start::timestamp with time zone",
    )
    op.alter_column(
        "missions",
        "planned_end",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="planned_end::timestamp with time zone",
    )
    op.drop_column("missions", "transport_modes")
