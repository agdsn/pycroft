"""Make address.state and addition not null

Revision ID: ce8c8cebcbf4
Revises: 38fa5154b920
Create Date: 2019-10-13 21:24:39.752497

"""
from alembic import op
import sqlalchemy as sa
import pycroft


# revision identifiers, used by Alembic.
revision = 'ce8c8cebcbf4'
down_revision = '38fa5154b920'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('address', 'addition',
                    existing_type=sa.VARCHAR(),
                    nullable=False,
                    server_default="")
    op.alter_column('address', 'state',
                    existing_type=sa.VARCHAR(),
                    nullable=False,
                    server_default="")


def downgrade():
    op.alter_column('address', 'state',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
    op.alter_column('address', 'addition',
                    existing_type=sa.VARCHAR(),
                    nullable=True)
