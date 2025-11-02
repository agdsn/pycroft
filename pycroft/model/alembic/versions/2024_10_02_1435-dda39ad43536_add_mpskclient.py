"""Add MPSKClient

Revision ID: dda39ad43536
Revises: 5234d7ac2b4a
Create Date: 2024-09-28 10:01:39.952235

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "dda39ad43536"
down_revision = "5234d7ac2b4a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mpsk_client",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("mac", postgresql.types.MACADDR, nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mac"),
    )
    op.create_index(op.f("ix_mpsk_client_owner_id"), "mpsk_client", ["owner_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_mpsk_client_owner_id"), table_name="mpsk_client")
    op.drop_table("mpsk_client")
