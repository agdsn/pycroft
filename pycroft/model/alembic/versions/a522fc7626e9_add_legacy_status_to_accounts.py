"""Add legacy status to accounts

Revision ID: a522fc7626e9
Revises: 305a51819d48
Create Date: 2019-06-08 15:41:16.250781

"""
from alembic import op
import sqlalchemy as sa
import pycroft


# revision identifiers, used by Alembic.
revision = 'a522fc7626e9'
down_revision = '305a51819d48'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('account', sa.Column('legacy', sa.Boolean(), nullable=False,
                                       server_default=sa.schema.DefaultClause("0")))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('account', 'legacy')
    # ### end Alembic commands ###
