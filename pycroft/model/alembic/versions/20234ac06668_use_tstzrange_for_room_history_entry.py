"""Use tstzrange for room_history_entry

Revision ID: 20234ac06668
Revises: f138079b24c5
Create Date: 2021-10-24 16:31:51.027020

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
from sqlalchemy.dialects.postgresql import TSTZRANGE

revision = '20234ac06668'
down_revision = 'f138079b24c5'
branch_labels = None
depends_on = None

RHE = 'room_history_entry'


def upgrade():
    # -UPDATE FUNCTION
    op.execute("drop function user_room_change_update_history cascade")
    op.execute("""\
CREATE OR REPLACE FUNCTION user_room_change_update_history() RETURNS trigger
    LANGUAGE plpgsql STRICT
    AS $$
            BEGIN
                IF old.room_id IS DISTINCT FROM new.room_id THEN
                    IF old.room_id IS NOT NULL THEN
                        /* User was living in a room before, history entry must be ended */
                        /* active_during is expected to be [) */
                        UPDATE "room_history_entry"
                            SET active_during = active_during - tstzrange(CURRENT_TIMESTAMP, null, '[)')
                            WHERE room_id = old.room_id AND user_id = new.id
                            AND active_during && tstzrange(CURRENT_TIMESTAMP, null, '[)');
                    END IF;

                    IF new.room_id IS NOT NULL THEN
                        /* User moved to a new room. history entry must be created */
                        INSERT INTO "room_history_entry" (user_id, room_id, active_during)
                            /* We must add one second so that the user doesn't have two entries
                               for the same timestamp */
                            VALUES(new.id, new.room_id, tstzrange(CURRENT_TIMESTAMP, null, '[)'));
                    END IF;
                END IF;
                RETURN NULL;
            END;
            $$;""")
    ###

    # +ACTIVE_DURING
    op.add_column(RHE,
                  sa.Column('active_during', TSTZRANGE, nullable=True))
    op.execute("update room_history_entry set active_during = tstzrange(begins_at, ends_at, '[)')")
    op.alter_column('membership', 'active_during', nullable=False)

    op.create_index('ix_room_history_entry_active_during', RHE, ['active_during'],
                    unique=False, postgresql_using='gist')
    op.execute("create extension if not exists btree_gist")
    op.execute(
        'alter table room_history_entry '
        'add constraint "room_history_entry_room_id_user_id_active_during_excl" '
        'EXCLUDE USING gist (room_id WITH =, user_id WITH =, active_during WITH &&);'
    )
    ###

    # -UNIQUENESS CHECK
    op.execute("drop function room_history_entry_uniqueness cascade")
    # also deletes the trigger
    ###

    op.drop_constraint('room_history_entry_check', table_name=RHE)
    op.drop_column(RHE, 'begins_at')
    op.drop_column(RHE, 'ends_at')


def downgrade():
    # +BEGINS_AT
    op.add_column(RHE, sa.Column(
        'begins_at', postgresql.TIMESTAMP(timezone=True),
        server_default=sa.text('CURRENT_TIMESTAMP'),
        autoincrement=False, nullable=False
    ))
    op.execute('update room_history_entry set begins_at = lower(active_during)')
    op.alter_column(RHE, 'begins_at', nullable=False)
    op.create_index('ix_room_history_entry_begins_at', RHE, ['begins_at'],
                    unique=False)
    ###

    # +ENDS_AT
    op.add_column(RHE,
                  sa.Column('ends_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False,
                            nullable=True))
    op.execute('update room_history_entry set ends_at = upper(active_during)')
    op.create_index('ix_room_history_entry_ends_at', RHE, ['ends_at'],
                    unique=False)
    ###

    op.create_check_constraint(
        "room_history_entry_check", RHE,
        "ends_at is null or begins_at <= ends_at",
    )

    # +UNIQUENESS CHECK
    op.execute("""\
CREATE FUNCTION room_history_entry_uniqueness() RETURNS trigger
    LANGUAGE plpgsql STABLE STRICT
    AS $$
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
        $$; """)
    op.execute(
        "CREATE TRIGGER room_history_entry_uniqueness_trigger "
        "AFTER INSERT OR UPDATE ON room_history_entry "
        "FOR EACH ROW EXECUTE PROCEDURE room_history_entry_uniqueness();"
    )
    ###

    # -ACTIVE_DURING
    op.drop_constraint(
        constraint_name='room_history_entry_room_id_user_id_active_during_excl',
        table_name=RHE,
    )
    op.drop_index('ix_room_history_entry_active_during', table_name=RHE,
                  postgresql_using='gist')
    op.drop_column(RHE, 'active_during')
    ###

    # +UPDATE_FUNCTION
    op.execute("""\
CREATE OR REPLACE FUNCTION user_room_change_update_history() RETURNS trigger
    LANGUAGE plpgsql STRICT
    AS $$
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
            $$;""")
    ###
