"""Add name attribute to Host

Revision ID: a32def81e36a
Revises: 4e7eb2d1e44e
Create Date: 2018-09-02 15:34:02.873730

"""
from alembic import op
import sqlalchemy as sa
import pycroft


# revision identifiers, used by Alembic.
revision = 'a32def81e36a'
down_revision = '4e7eb2d1e44e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('host', sa.Column('name', sa.String(), nullable=True))


def downgrade():
    op.drop_column('host', 'name')
