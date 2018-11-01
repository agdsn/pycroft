"""Make membership fees more flexible

Revision ID: 92ee63f41c5b
Revises: 6f1a37baa574
Create Date: 2018-11-01 14:57:25.498035

"""
from datetime import timedelta

from alembic import op
import sqlalchemy as sa
import pycroft
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '92ee63f41c5b'
down_revision = '6f1a37baa574'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('membership_fee', sa.Column('booking_begin', sa.Interval(), nullable=True))
    op.add_column('membership_fee', sa.Column('booking_end', sa.Interval(), nullable=True))
    op.drop_column('membership_fee', 'grace_period')

    membership_fee = sa.table('membership_fee',
                        sa.Column('booking_begin', sa.Interval(), nullable=False),
                        sa.Column('booking_end', sa.Interval(), nullable=False))

    op.execute(membership_fee.update()
               .values({'booking_begin': timedelta(days=2),
                        'booking_end': timedelta(days=14)}))

    op.alter_column('membership_fee', sa.Column('booking_begin',nullable=False))
    op.alter_column('membership_fee', sa.Column('booking_end', nullable=False))


def downgrade():
    op.add_column('membership_fee', sa.Column('grace_period', postgresql.INTERVAL(), autoincrement=False, nullable=False))
    op.drop_column('membership_fee', 'booking_end')
    op.drop_column('membership_fee', 'booking_begin')

    membership_fee = sa.table('membership_fee',
                              sa.Column('grace_period', sa.Interval(),
                                        nullable=False))

    op.execute(membership_fee.update()
               .values({'grace_period': timedelta(days=14)}))
