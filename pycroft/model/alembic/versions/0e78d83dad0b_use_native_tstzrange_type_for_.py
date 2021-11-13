"""Use native tstzrange type for membership table

Revision ID: 0e78d83dad0b
Revises: 27f7f8832dfa
Create Date: 2021-10-23 17:31:29.093581

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import TSTZRANGE

# revision identifiers, used by Alembic.
revision = '0e78d83dad0b'
down_revision = '27f7f8832dfa'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('membership', sa.Column('active_during', TSTZRANGE))
    op.execute("update membership set active_during = tstzrange(begins_at, ends_at, '[]')")
    op.alter_column('membership', 'active_during', nullable=False)

    op.drop_index('ix_membership_begins_at', table_name='membership')
    op.drop_index('ix_membership_ends_at', table_name='membership')
    op.create_index('ix_active_during', 'membership', ['active_during'],
                    unique=False, postgresql_using='gist')
    op.drop_column('membership', 'ends_at')
    op.drop_column('membership', 'begins_at')

    op.execute("""
    CREATE OR REPLACE FUNCTION public.evaluate_properties(evaluation_time timestamp with time zone)
        RETURNS TABLE
                (
                    user_id       integer,
                    property_name character varying,
                    denied        boolean
                )
        LANGUAGE sql
        STABLE
    AS $function$
    SELECT "user".id AS user_id, property.name AS property_name, false AS denied
    FROM membership
             JOIN ("group" JOIN property_group ON "group".id = property_group.id)
                  ON "group".id = membership.group_id
             JOIN "user" ON "user".id = membership.user_id
             JOIN property ON property_group.id = property.property_group_id
    WHERE membership.active_during @> evaluation_time
    GROUP BY "user".id, property.name
    HAVING every(property.granted)
    UNION
    SELECT "user".id AS user_id, property.name AS property_name, true AS denied
    FROM membership
             JOIN ("group" JOIN property_group ON "group".id = property_group.id)
                  ON "group".id = membership.group_id
             JOIN "user" ON "user".id = membership.user_id
             JOIN property ON property_group.id = property.property_group_id
    WHERE membership.active_during @> evaluation_time
    GROUP BY "user".id, property.name
    HAVING bool_or(property.granted) AND NOT every(property.granted)
    $function$ """)


def downgrade():
    op.add_column('membership', sa.Column('begins_at', postgresql.TIMESTAMP(timezone=True),
                                          server_default=sa.text('CURRENT_TIMESTAMP'),
                                          autoincrement=False))
    op.execute('update membership set begins_at = lower(active_during)')
    op.alter_column('membership', 'begins_at', nullable=False)

    op.add_column('membership', sa.Column('ends_at', postgresql.TIMESTAMP(timezone=True),
                                          autoincrement=False, nullable=True))
    op.execute('update membership set ends_at = upper(active_during)')

    op.drop_index('ix_active_during', table_name='membership', postgresql_using='gist')
    op.create_index('ix_membership_ends_at', 'membership', ['ends_at'], unique=False)
    op.create_index('ix_membership_begins_at', 'membership', ['begins_at'], unique=False)
    op.drop_column('membership', 'active_during')

    op.execute("""
    CREATE OR REPLACE FUNCTION public.evaluate_properties(evaluation_time timestamp with time zone)
    RETURNS TABLE
            (
                user_id       integer,
                property_name character varying,
                denied        boolean
            )
    LANGUAGE sql
    STABLE
    AS $function$
    SELECT "user".id AS user_id, property.name AS property_name, false AS denied
    FROM membership
             JOIN ("group" JOIN property_group ON "group".id = property_group.id)
                  ON "group".id = membership.group_id
             JOIN "user" ON "user".id = membership.user_id
             JOIN property ON property_group.id = property.property_group_id
    WHERE (membership.begins_at IS NULL OR membership.begins_at <= evaluation_time)
      AND (membership.ends_at IS NULL OR evaluation_time <= membership.ends_at)
    GROUP BY "user".id, property.name
    HAVING every(property.granted)
    UNION
    SELECT "user".id AS user_id, property.name AS property_name, true AS denied
    FROM membership
             JOIN ("group" JOIN property_group ON "group".id = property_group.id)
                  ON "group".id = membership.group_id
             JOIN "user" ON "user".id = membership.user_id
             JOIN property ON property_group.id = property.property_group_id
    WHERE (membership.begins_at IS NULL OR membership.begins_at <= evaluation_time)
      AND (membership.ends_at IS NULL OR evaluation_time <= membership.ends_at)
    GROUP BY "user".id, property.name
    HAVING bool_or(property.granted) AND NOT every(property.granted)
    $function$ """)
