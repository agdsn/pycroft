"""add fints product id

Revision ID: 3ec1d29bfd10
Revises: 37b57e0baa3a
Create Date: 2020-05-06 21:02:42.433050

"""
from alembic import op
import sqlalchemy as sa
import pycroft


# revision identifiers, used by Alembic.
revision = '3ec1d29bfd10'
down_revision = '37b57e0baa3a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('config',
                  sa.Column('fints_product_id', sa.String(), nullable=True))


def downgrade():
    op.drop_column('config', 'fints_product_id')
