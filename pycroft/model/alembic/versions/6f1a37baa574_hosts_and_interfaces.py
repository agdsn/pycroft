"""hosts and interfaces

Revision ID: 6f1a37baa574
Revises: cd588620e7d0
Create Date: 2018-09-17 15:38:56.401301

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import table, column, String

import pycroft


# revision identifiers, used by Alembic.
revision = '6f1a37baa574'
down_revision = 'cd588620e7d0'
branch_labels = None
depends_on = None


def upgrade():
    property = table('property', column('name', String))

    op.execute(property.update().where(property.c.name == op.inline_literal('user_mac_change'))
               .values({'name':op.inline_literal('user_hosts_change')}))


def downgrade():
    property = table('property', column('name', String))

    op.execute(property.update().where(
        property.c.name == op.inline_literal('user_hosts_change'))
               .values({'name': op.inline_literal('user_mac_change')}))
