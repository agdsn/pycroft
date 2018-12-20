"""add table for mt940 parsing errors

Revision ID: 8ff6f90b98fa
Revises: 08fa5b3cc555
Create Date: 2018-12-20 18:34:05.289624

"""
from alembic import op
import sqlalchemy as sa
import pycroft
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8ff6f90b98fa'
down_revision = '08fa5b3cc555'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('mt940_error',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('mt940', sa.Text(), nullable=False),
    sa.Column('exception', sa.Text(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=False),
    sa.Column('imported_at', pycroft.model.types.DateTimeTz(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('bank_account_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['bank_account_id'], ['bank_account.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('mt940_error')
