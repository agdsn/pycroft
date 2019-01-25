"""Remove traffic credit and groups

Revision ID: 9a291ca0e06e
Revises: 7a6449f2489c
Create Date: 2019-01-25 15:38:52.300698

"""
from alembic import op
import sqlalchemy as sa
import pycroft
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9a291ca0e06e'
down_revision = '7a6449f2489c'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    op.drop_index('ix_traffic_credit_user_id', table_name='traffic_credit')

    conn.execute(sa.text("DROP VIEW current_traffic_balance"))

    op.drop_index('ix_building_default_traffic_group_id', table_name='building')
    op.drop_constraint('building_default_traffic_group_id_fkey', 'building',
                       type_='foreignkey')
    op.drop_column('building', 'default_traffic_group_id')

    op.drop_table('traffic_credit')
    op.drop_table('traffic_group')
    op.drop_table('traffic_balance')


def downgrade():
    op.create_table('traffic_group',
    sa.Column('id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('credit_limit', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('credit_interval', postgresql.INTERVAL(), autoincrement=False, nullable=False),
    sa.Column('credit_amount', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('initial_credit_amount', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['id'], ['group.id'], name='traffic_group_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='traffic_group_pkey'),
    postgresql_ignore_search_path=False
    )

    op.add_column('building', sa.Column('default_traffic_group_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('building_default_traffic_group_id_fkey', 'building', 'traffic_group', ['default_traffic_group_id'], ['id'])
    op.create_index('ix_building_default_traffic_group_id', 'building', ['default_traffic_group_id'], unique=False)
    op.create_table('traffic_balance',
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('amount', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('timestamp', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='traffic_balance_user_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id', name='traffic_balance_pkey')
    )

    op.create_table('traffic_credit',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('timestamp', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), autoincrement=False, nullable=False),
    sa.Column('amount', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.CheckConstraint('amount >= 0', name='traffic_credit_amount_check'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='traffic_credit_user_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='traffic_credit_pkey')
    )
    op.create_index('ix_traffic_credit_user_id', 'traffic_credit', ['user_id'], unique=False)

    # TODO: Recreate current_traffic_balance view
