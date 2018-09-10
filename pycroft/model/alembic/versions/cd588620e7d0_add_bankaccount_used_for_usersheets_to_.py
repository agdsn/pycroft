"""add BankAccount used for usersheets to config

Revision ID: cd588620e7d0
Revises: a32def81e36a
Create Date: 2018-09-10 21:54:26.977248

"""
from alembic import op
import sqlalchemy as sa
import pycroft


# revision identifiers, used by Alembic.
revision = 'cd588620e7d0'
down_revision = 'a32def81e36a'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    # ### commands auto generated by Alembic - please adjust! ###
    # server_default=1: BankAccount with ID 1 is the BankAccount which should be used
    op.add_column('config', sa.Column('membership_fee_bank_account_id', sa.Integer(), nullable=False, server_default='1'))
    op.create_foreign_key(None, 'config', 'bank_account', ['membership_fee_bank_account_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'config', type_='foreignkey')
    op.drop_column('config', 'membership_fee_bank_account_id')
    # ### end Alembic commands ###
