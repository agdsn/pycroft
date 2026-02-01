"""add bankaccount owner

Revision ID: bc0e0dd480d4
Revises: 55e9f0d9b5f4
Create Date: 2024-03-16 08:42:48.684471

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "bc0e0dd480d4"
down_revision = "55e9f0d9b5f4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "bank_account", sa.Column("owner", sa.String(length=255), nullable=False, server_default="")
    )


def downgrade():
    op.drop_column("bank_account", "owner")
