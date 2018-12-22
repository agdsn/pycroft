"""infrastructure change

Revision ID: 7a6449f2489c
Revises: 8ff6f90b98fa
Create Date: 2018-12-20 23:10:49.889221

"""
from alembic import op
import sqlalchemy as sa
import pycroft


# revision identifiers, used by Alembic.
revision = '7a6449f2489c'
down_revision = '8ff6f90b98fa'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('patch_port', sa.Column('switch_room_id', sa.Integer(), nullable=True))

    host = sa.table('host', sa.column('room_id', sa.Integer),
                            sa.column('id', sa.Integer),
                            sa.column('name', sa.String))
    switch_port = sa.table('switch_port', sa.column('switch_id', sa.Integer),
                                          sa.column('id', sa.Integer))
    switch = sa.table('switch', sa.column('host_id', sa.Integer),
                                sa.column('name', sa.String))
    patch_port = sa.table('patch_port',
                          sa.column('switch_room_id', sa.Integer),
                          sa.column('switch_port_id', sa.Integer),
                          sa.column('id', sa.Integer))

    # Set patch_port.switch_room_id to patch_port.switch_port.switch.host.id
    op.execute(patch_port.update().values(
        switch_room_id=sa.select([host.c.room_id])
                         .select_from(patch_port.alias("patch_port_subselect")
                                      .join(switch_port, patch_port.c.switch_port_id == switch_port.c.id)
                                      .join(host, switch_port.c.switch_id == host.c.id))
                         .where(sa.literal_column('patch_port_subselect.id') == patch_port.c.id)
    ))

    op.alter_column('patch_port', 'switch_room_id', nullable=False)

    op.create_index(op.f('ix_patch_port_switch_room_id'), 'patch_port', ['switch_room_id'], unique=False)
    op.create_unique_constraint("patch_port_name_switch_room_id_key", 'patch_port', ['name', 'switch_room_id'])
    op.create_foreign_key("patch_port_switch_room_id_fkey", 'patch_port', 'room', ['switch_room_id'], ['id'])

    # Set switch.host.name to switch.name
    op.execute(host.update().values(
        name=sa.select([switch.c.name])
               .select_from(host.alias("host_subselect")
                            .join(switch, switch.c.host_id == host.c.id))
               .where(sa.literal_column('host_subselect.id') == switch.c.host_id)
    ))

    op.drop_column('switch', 'name')

    # Create patch_port_switch_in_switch_room function and trigger
    op.execute('''
        CREATE OR REPLACE FUNCTION patch_port_switch_in_switch_room() RETURNS trigger STABLE STRICT LANGUAGE plpgsql AS $$
        DECLARE
          v_patch_port patch_port;
          v_switch_port_switch_host_room_id integer;
        BEGIN
          v_patch_port := NEW;

          IF v_patch_port.switch_port_id IS NOT NULL THEN
              SELECT h.room_id INTO v_switch_port_switch_host_room_id FROM patch_port pp
                  JOIN switch_port sp ON pp.switch_port_id = sp.id
                  JOIN host h ON sp.switch_id = h.id
                  WHERE pp.id = v_patch_port.id;

              IF v_switch_port_switch_host_room_id <> v_patch_port.switch_room_id THEN
                RAISE EXCEPTION 'A patch-port can only be patched to a switch that is located in the switch-room of
                                  the patch-port';
              END IF;
          END IF;
          RETURN NULL;
        END;
        $$
    ''')
    op.execute('''
        CREATE CONSTRAINT TRIGGER patch_port_switch_in_switch_room_trigger
        AFTER INSERT OR UPDATE
        ON patch_port
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE PROCEDURE patch_port_switch_in_switch_room()
    ''')


def downgrade():
    op.drop_constraint("patch_port_switch_room_id_fkey", 'patch_port', type_='foreignkey')
    op.drop_constraint("patch_port_name_switch_room_id_key", 'patch_port', type_='unique')
    op.drop_index(op.f('ix_patch_port_switch_room_id'), table_name='patch_port')
    op.drop_column('patch_port', 'switch_room_id')

    op.add_column('switch', sa.Column('name', sa.String(127), nullable=True))

    host = sa.table('host',
                    sa.column('id', sa.Integer),
                    sa.column('name', sa.String))
    switch = sa.table('switch', sa.column('host_id', sa.Integer),
                      sa.column('name', sa.String))

    # Set switch.name to switch.host.name
    op.execute(switch.update().values(
        name=sa.select([host.c.name])
            .select_from(switch.alias("switch_subselect")
                         .join(host, switch.c.host_id == host.c.id))
            .where(sa.literal_column('switch_subselect.host_id') == host.c.id)
    ))

    op.alter_column('switch', 'name', nullable=False)

    # Drop patch_port_switch_in_switch_room function and trigger
    op.execute('DROP TRIGGER IF EXISTS patch_port_switch_in_switch_room_trigger ON patch_port')
    op.execute('DROP FUNCTION IF EXISTS patch_port_switch_in_switch_room()')
