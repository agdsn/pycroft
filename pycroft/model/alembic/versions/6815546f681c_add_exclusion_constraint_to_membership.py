"""Add exclusion constraint to membership

Revision ID: 6815546f681c
Revises: 20234ac06668
Create Date: 2021-11-14 00:38:58.192514

"""
from alembic import op
import sqlalchemy as sa
import pycroft


# revision identifiers, used by Alembic.
revision = '6815546f681c'
down_revision = '20234ac06668'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        alter table membership
        add constraint "membership_group_id_user_id_active_during_excl"
        EXCLUDE USING gist (group_id with =, user_id with =, active_during with &&);
    """)
    op.execute("alter index ix_active_during rename to ix_membership_active_during")


def downgrade():
    op.drop_constraint(
        'membership_group_id_user_id_active_during_excl',
        table_name='membership',
    )
    op.execute("alter index ix_membership_active_during rename to ix_active_during")
