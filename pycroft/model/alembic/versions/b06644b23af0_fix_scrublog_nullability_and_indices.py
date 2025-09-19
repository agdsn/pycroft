"""Fix scrublog nullability and indices

Revision ID: b06644b23af0
Revises: aeb6fcee82a4
Create Date: 2025-09-19 09:31:09.003313

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b06644b23af0'
down_revision = 'aeb6fcee82a4'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('scrub_log', 'executed_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('scrub_log', 'scrubber',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('scrub_log', 'info',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               nullable=False)
    op.drop_index('ix_info', table_name='scrub_log')
    op.create_index(op.f('ix_scrub_log_executed_at'), 'scrub_log', ['executed_at'], unique=False)
    op.create_index(op.f('ix_scrub_log_info'), 'scrub_log', ['info'], unique=False)
    op.create_index(op.f('ix_scrub_log_scrubber'), 'scrub_log', ['scrubber'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_scrub_log_scrubber'), table_name='scrub_log')
    op.drop_index(op.f('ix_scrub_log_info'), table_name='scrub_log')
    op.drop_index(op.f('ix_scrub_log_executed_at'), table_name='scrub_log')
    op.create_index('ix_info', 'scrub_log', ['info'], unique=False)
    op.alter_column('scrub_log', 'info',
               existing_type=postgresql.JSONB(astext_type=sa.Text()),
               nullable=True)
    op.alter_column('scrub_log', 'scrubber',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('scrub_log', 'executed_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
