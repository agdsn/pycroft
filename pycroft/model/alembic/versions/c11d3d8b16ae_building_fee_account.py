"""building_fee_account

Revision ID: c11d3d8b16ae
Revises: 3ec1d29bfd10
Create Date: 2020-02-26 23:05:46.376751

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c11d3d8b16ae'
down_revision = '3ec1d29bfd10'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('building', sa.Column('fee_account_id', sa.Integer(), nullable=True))
    op.create_foreign_key('building_fee_account_id_fkey', 'building', 'account',
                          ['fee_account_id'], ['id'])

    op.execute("update building set fee_account_id=19 where true")

    op.alter_column('building', 'fee_account_id', nullable=False)

    # Make beginning of a membership not nullable as it makes no sense
    op.alter_column('membership', 'begins_at', nullable=False)

    # Add missing check constraint for memberships
    op.create_check_constraint(
        "membership_check",
        "membership",
        "ends_at IS NULL OR begins_at <= ends_at",
    )

    op.create_table('room_history_entry',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('room_id', sa.Integer(), nullable=False),
                    sa.Column('begins_at', postgresql.TIMESTAMP(timezone=True), nullable=False,
                              server_default=sa.func.current_timestamp()),
                    sa.Column('ends_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
                    sa.ForeignKeyConstraint(('user_id',), ['user.id'], ),
                    sa.ForeignKeyConstraint(('room_id',), ['room.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.CheckConstraint("ends_at IS NULL OR begins_at <= ends_at"), )

    # Trigger to keep room history up-to-date

    op.execute('''
            create or replace function user_room_change_update_history() returns trigger
                strict
                language plpgsql
            as $$
            BEGIN
                IF old.room_id IS DISTINCT FROM new.room_id THEN
                    IF old.room_id IS NOT NULL THEN
                        /* User was living in a room before, history entry must be ended */
                        UPDATE "room_history_entry" SET ends_at = CURRENT_TIMESTAMP
                            WHERE user_id = new.id AND ends_at IS NULL;
                    END IF;

                    IF new.room_id IS NOT NULL THEN
                        /* User moved to a new room. history entry must be created */
                        INSERT INTO "room_history_entry" (user_id, room_id, begins_at)
                            /* We must add one second so that the user doesn't have two entries
                               for the same timestamp */
                            VALUES(new.id, new.room_id, CURRENT_TIMESTAMP + INTERVAL '1' second);
                    END IF;
                END IF;
                RETURN NULL;
            END;
            $$;
        ''')

    op.execute('''
        create trigger user_room_change_update_history_trigger
        after insert or update
        on "user"
        for each row
        execute procedure user_room_change_update_history();
    ''')

    # Constraint trigger to make sure that no overlapping room history entries exist

    op.execute('''
        create function room_history_entry_uniqueness() returns trigger
            stable
            strict
            language plpgsql
        as
        $$
        DECLARE
          rhe_id integer;
          count integer;
        BEGIN
            SELECT COUNT(*), MAX(rhe.id) INTO STRICT count, rhe_id FROM "room_history_entry" rhe
              WHERE
              (tstzrange(NEW.begins_at,
                               COALESCE(new.ends_at, 'infinity'::timestamp),
                               '()')
              &&
              tstzrange(rhe.begins_at,
                           COALESCE(rhe.ends_at, 'infinity'::timestamp),
                           '()')
              )
              AND NEW.user_id = rhe.user_id AND NEW.id != rhe.id;

            IF count > 0 THEN
                RAISE EXCEPTION 'entry overlaps with entry %',
                rhe_id
                USING ERRCODE = 'integrity_constraint_violation';
            END IF;

            RETURN NULL;
        END;
        $$;
    ''')

    op.execute('''
        create trigger room_history_entry_uniqueness_trigger
        after insert or update
        on room_history_entry
        for each row
        execute procedure room_history_entry_uniqueness();
    ''')

    # Insert room history entries for all users living in a dorm beginning with their registration

    op.execute(
        """INSERT INTO room_history_entry (user_id, room_id, begins_at)
        SELECT "user".id, "user".room_id, "user".registered_at
        FROM "user"
        WHERE "user".room_id IS NOT NULL"""
    )

    # Update membership_fee constraint
    op.execute("alter table membership_fee drop constraint membership_fee_check")

    op.create_check_constraint(
        "membership_fee_check",
        "membership_fee",
        "begins_on <= ends_on",
    )

def downgrade():
    op.drop_constraint('building_fee_account_id_fkey', 'building', type_='foreignkey')
    op.drop_column('building', 'fee_account_id')

    op.execute('drop trigger if exists "user_room_change_update_history_trigger" on "user"')
    op.execute('drop function if exists user_room_change_update_history();')

    op.alter_column('membership', 'begins_at', nullable=True)
    op.drop_constraint('membership_check', 'membership', type_='check')

    op.drop_table("room_history_entry")
    op.execute('drop function if exists room_history_entry_uniqueness();')

    op.execute("alter table membership_fee drop constraint membership_fee_check")
    op.create_check_constraint(
        "membership_fee_check",
        "membership_fee",
        "begins_on < ends_on",
    )
