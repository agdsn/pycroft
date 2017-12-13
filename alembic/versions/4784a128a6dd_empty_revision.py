"""Empty revision

This is the empty revision that can be used as the base for future
migrations.

Initial database creation shall be done via `metadata.create_all()` and
`alembic stamp head`.

Revision ID: 4784a128a6dd
Revises:
Create Date: 2017-12-13 00:48:12.079431

"""

from alembic import op
import sqlalchemy as sa
import pycroft


# revision identifiers, used by Alembic.
revision = '4784a128a6dd'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
