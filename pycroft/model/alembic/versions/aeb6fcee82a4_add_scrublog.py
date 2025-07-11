"""Add scrublog

Revision ID: aeb6fcee82a4
Revises: b64618e97415
Create Date: 2025-07-11 20:27:13.779327

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "aeb6fcee82a4"
down_revision = "b64618e97415"
branch_labels = None
depends_on = None


def upgrade():
    _ = op.create_table(
        "scrub_log",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column(
            "executed_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("scrubber_name", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column(
            "scrub_info",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )
    _ = op.create_index("ix_scrub_info", "scrub_log", ["scrub_info"], unique=False)


def downgrade():
    _ = op.drop_index("ix_scrub_info", table_name="scrub_log")
    op.drop_table("scrub_log")
