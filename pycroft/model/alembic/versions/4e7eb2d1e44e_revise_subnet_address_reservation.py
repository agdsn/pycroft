"""Revise subnet address reservation

Revision ID: 4e7eb2d1e44e
Revises: 4784a128a6dd
Create Date: 2018-09-01 09:06:06.227707

"""
from alembic import op
import sqlalchemy as sa
import pycroft

# revision identifiers, used by Alembic.
revision = '4e7eb2d1e44e'
down_revision = '4784a128a6dd'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('subnet', 'reserved_addresses',
                    new_column_name='reserved_addresses_bottom', nullable=False,
                    server_default=sa.text('0'))
    op.add_column('subnet', sa.Column('reserved_addresses_top', sa.Integer(),
                                      server_default=sa.text('0'),
                                      nullable=False))


def downgrade():
    op.alter_column('subnet', 'reserved_addresses_bottom',
                    new_column_name='reserved_addresses', nullable=True,
                    server_default=None)
    op.drop_column('subnet', 'reserved_addresses_top')
