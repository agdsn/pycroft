"""add BankAccount used for usersheets to config

Revision ID: cd588620e7d0
Revises: a32def81e36a
Create Date: 2018-09-10 21:54:26.977248

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table
import pycroft


# revision identifiers, used by Alembic.
revision = 'cd588620e7d0'
down_revision = 'a32def81e36a'
branch_labels = None
depends_on = None


def upgrade():
    # has to be nullable since there is actually no data...
    op.add_column('config', sa.Column('membership_fee_bank_account_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'config', 'bank_account', ['membership_fee_bank_account_id'], ['id'])
    # ...insert data...
    config = table(
        'config',
        sa.Column('membership_fee_bank_account_id', sa.Integer()),
        # Other columns not needed for the data migration
    )
    op.execute(
        config
            .update()
            .values({'membership_fee_bank_account_id': 1})
    )
    # ...set NOT NULL
    op.alter_column('config', 'membership_fee_bank_account_id', nullable=False)


def downgrade():
    op.drop_constraint(None, 'config', type_='foreignkey')
    op.drop_column('config', 'membership_fee_bank_account_id')
