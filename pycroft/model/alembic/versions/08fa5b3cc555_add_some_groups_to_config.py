"""add some groups to config

Revision ID: 08fa5b3cc555
Revises: 92ee63f41c5b
Create Date: 2018-11-27 21:41:36.657526

"""
from alembic import op
import sqlalchemy as sa
import pycroft


# revision identifiers, used by Alembic.
revision = '08fa5b3cc555'
down_revision = '92ee63f41c5b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('config', sa.Column('blocked_group_id', sa.Integer(), nullable=False, server_default='10'))
    op.add_column('config', sa.Column('caretaker_group_id', sa.Integer(), nullable=False, server_default='11'))

    op.create_foreign_key(None, 'config', 'property_group', ['blocked_group_id'], ['id'])
    op.create_foreign_key(None, 'config', 'property_group', ['caretaker_group_id'], ['id'])

    op.alter_column('config', 'blocked_group_id', server_default=None)
    op.alter_column('config', 'caretaker_group_id', server_default=None)


def downgrade():
    op.drop_constraint('config_caretaker_group_id_fkey', 'config', type_='foreignkey')
    op.drop_constraint('config_blocked_group_id_fkey', 'config', type_='foreignkey')
    op.drop_column('config', 'caretaker_group_id')
    op.drop_column('config', 'blocked_group_id')
