"""Use bytea instead of textfor web_storage.data

Revision ID: f138079b24c5
Revises: 0e78d83dad0b
Create Date: 2021-10-24 15:06:41.186366

"""
from alembic import op
import sqlalchemy as sa
import pycroft


# revision identifiers, used by Alembic.
revision = 'f138079b24c5'
down_revision = '0e78d83dad0b'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('web_storage', 'data', type_=sa.LargeBinary(),
                    postgresql_using="decode(data, 'base64')")


def downgrade():
    op.alter_column('web_storage', 'data', type_=sa.Text(),
                    postgresql_using="encode(data, 'base64')")
