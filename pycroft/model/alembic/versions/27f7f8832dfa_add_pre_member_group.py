"""add pre member account

Revision ID: 27f7f8832dfa
Revises: fb8d553a7268
Create Date: 2021-06-02 10:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '27f7f8832dfa'
down_revision = 'fb8d553a7268'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('config', sa.Column('pre_member_group_id', sa.Integer(), nullable=False,
                                      server_default='20'))
    op.create_foreign_key('config_pre_member_group_id_fkey',
                          'config', 'property_group', ['pre_member_group_id'], ['id'])

    op.alter_column('config', 'pre_member_group_id', server_default=None)


def downgrade():
    op.drop_column('config', 'pre_member_group_id')
    op.drop_constraint('config_pre_member_group_id_fkey', 'config', type_='foreignkey')
