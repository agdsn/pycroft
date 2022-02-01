"""Add confirmed status to transaction

Revision ID: ae8f4b63876a
Revises: 7c1927c937af
Create Date: 2019-05-31 18:08:19.462983

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'ae8f4b63876a'
down_revision = '7c1927c937af'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('transaction', sa.Column('confirmed', sa.Boolean(), nullable=False, server_default=sa.schema.DefaultClause("1")))
    # ### end Alembic commands ###

    op.add_column('config',
                  sa.Column('treasurer_group_id', sa.Integer(), nullable=False,
                            server_default='13'))

    op.create_foreign_key(None, 'config', 'property_group',
                          ['treasurer_group_id'], ['id'])

    op.alter_column('config', 'treasurer_group_id', server_default=None)


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('transaction', 'confirmed')
    # ### end Alembic commands ###

    op.drop_constraint('config_treasurer_group_id_fkey', 'config',
                       type_='foreignkey')
    op.drop_column('config', 'treasurer_group_id')
