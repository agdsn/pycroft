"""drop_mt940

Revision ID: a0fd5bf93d1d
Revises: 82f43cfa0f98
Create Date: 2026-03-22 00:18:26.005888+00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a0fd5bf93d1d"
down_revision = "82f43cfa0f98"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("mt940_error")


def downgrade():
    op.create_table(
        "mt940_error",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mt940", sa.Text(), nullable=False),
        sa.Column("exception", sa.Text(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column(
            "imported_at",
            sa.types.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("bank_account_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["bank_account_id"],
            ["bank_account.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
