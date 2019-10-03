"""Add address relation

Revision ID: ff700db83195
Revises: f85ef1ef556c
Create Date: 2019-10-03 19:15:55.716640

"""
from typing import List, Callable

import sqlalchemy as sa
from alembic import op
from sqlalchemy import orm

from sqlalchemy.ext.declarative import declarative_base

# revision identifiers, used by Alembic.
revision = 'ff700db83195'
down_revision = 'f85ef1ef556c'
branch_labels = None
depends_on = None

Base = declarative_base()

DEFAULT_CITY = "Dresden"
DEFAULT_STATE = "Sachsen"
DEFAULT_COUNTRY = "Germany"


class _Address(Base):
    """A baked version of the Address table for easier data migration"""
    __tablename__ = 'address'
    id = sa.Column(sa.Integer, primary_key=True)
    street = sa.Column(sa.String(), nullable=False)
    number = sa.Column(sa.String(), nullable=False)
    addition = sa.Column(sa.String())
    zip_code = sa.Column(sa.String(), nullable=False, default="01217")
    city = sa.Column(sa.String(), nullable=False, default=DEFAULT_CITY)
    state = sa.Column(sa.String(), nullable=False, default=DEFAULT_STATE)
    country = sa.Column(sa.String(), nullable=False, default=DEFAULT_COUNTRY)

    # temporary columns for easier data migration
    tmp_building_id = sa.Column(sa.Integer, nullable=True)
    building = orm.relationship(
        '_Building',
        primaryjoin='foreign(_Address.tmp_building_id) == _Building.id'
    )

    tmp_room_id = sa.Column(sa.Integer, nullable=True)
    room = orm.relationship(
        '_Room',
        primaryjoin='foreign(_Address.tmp_room_id) == _Room.id'
    )


# These are subsets of tables as they are on the base revision
class _Building(Base):
    __tablename__ = 'building'
    id = sa.Column(sa.Integer, primary_key=True)
    number = sa.Column(sa.String())
    short_name = sa.Column(sa.String())
    street = sa.Column(sa.String())


class _Room(Base):
    __tablename__ = 'room'
    id = sa.Column(sa.Integer, primary_key=True)
    number = sa.Column(sa.String())
    level = sa.Column(sa.Integer)
    inhabitable = sa.Column(sa.Boolean)
    building_id = sa.Column(sa.Integer, sa.ForeignKey(_Building.id))
    building = orm.relationship(_Building)


class _RoomAfter(_Room):
    address_id = sa.Column(sa.Integer, sa.ForeignKey(_Address.id))


class _User(Base):
    __tablename__ = 'user'
    id = sa.Column(sa.Integer, primary_key=True)
    login = sa.Column(sa.String(40), nullable=False, unique=True)
    room_id = sa.Column(sa.Integer, sa.ForeignKey(_Room.id))
    room = orm.relationship(_Room)


class _UserAfter(_User):
    address_id = sa.Column(sa.Integer, sa.ForeignKey(_Address.id))


def upgrade():
    cleanups: List[Callable] = []
    # SCHEMA MIGRATION
    # renaming constraint 'address' → 'building_address'
    op.create_unique_constraint('building_address', 'building', ['street', 'number'])
    op.drop_constraint('address', 'building', type_='unique')

    op.create_table(
        'address',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('street', sa.String(), nullable=False),
        sa.Column('number', sa.String(), nullable=False),
        sa.Column('addition', sa.String(), nullable=True),
        sa.Column('zip_code', sa.String(), nullable=False),
        sa.Column('city', sa.String(), nullable=False, server_default=DEFAULT_CITY),
        sa.Column('state', sa.String(), nullable=False, server_default=DEFAULT_STATE),
        sa.Column('country', sa.String(), nullable=False, server_default=DEFAULT_COUNTRY),

        # Temporary columns
        sa.Column('tmp_building_id', sa.Integer, nullable=True),
        sa.Column('tmp_room_id', sa.Integer, nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('street', 'number', 'addition', 'zip_code', 'city',
                            'state', 'country')
    )
    cleanups.append(lambda: op.drop_column('address', 'tmp_building_id'))
    cleanups.append(lambda: op.drop_column('address', 'tmp_room_id'))

    bind = op.get_bind()
    session = orm.Session(bind=bind)

    # DATA MIGRATION I: add dummy address
    dummy_id = add_dummy_address(session)
    dummy_default_cause = sa.schema.DefaultClause(f"{dummy_id}")

    # FURTHER SCHEMA MIGRATION…
    op.add_column('config', sa.Column('dummy_address_id', sa.Integer(), nullable=False,
                                      server_default=dummy_default_cause))
    cleanups.append(lambda: op.alter_column('config', 'dummy_address_id', server_default=None))
    op.create_foreign_key(None, 'config', 'address', ['dummy_address_id'], ['id'])

    # DATA MIGRATION II: add building addresses
    add_building_addresses(session)

    # DATA MIGRATION III: add room addresses
    add_room_addresses(session)

    # FURTHER SCHEMA MIGRATION…
    op.add_column('room', sa.Column('address_id', sa.Integer(), nullable=False,
                                    server_default=dummy_default_cause))
    cleanups.append(lambda: op.alter_column('room', 'address_id', server_default=None))
    op.create_index(op.f('ix_room_address_id'), 'room', ['address_id'], unique=False)
    op.create_foreign_key(None, 'room', 'address', ['address_id'], ['id'])

    # DATA MIGRATION IV: set `address_id` to building's address for uninhabitable rooms
    set_uninhabitable_room_addresses(session)

    # DATA MIGRATION IV: set `address_id` to room's address for inhabitable rooms
    set_inhabitable_room_addresses(session)

    # FURTHER SCHEMA MIGRATION…
    op.add_column('user', sa.Column('address_id', sa.Integer(), nullable=False,
                                    server_default=dummy_default_cause))
    cleanups.append(lambda: op.alter_column('user', 'address_id', server_default=None))
    op.create_index(op.f('ix_user_address_id'), 'user', ['address_id'], unique=False)
    op.create_foreign_key(None, 'user', 'address', ['address_id'], ['id'])

    # DATA MIGRATION VI: set `user.address` for users with room
    set_user_addresses(session)

    # FURTHER SCHEMA MIGRATION (cleanup)
    for action in cleanups:
        action()


def set_user_addresses(session):
    session.execute(
        sa.update(_User)
        .values(address_id=_RoomAfter.address_id)
        .where(_RoomAfter.id == _User.room_id)  # implies `room_id` is not null
    )


def set_inhabitable_room_addresses(session):
    session.execute(
        sa.update(_Room)
        .where(_Room.inhabitable)
        .values(address_id=_Address.id)
        .where(_Room.id == _Address.tmp_room_id)
    )


def set_uninhabitable_room_addresses(session):
    session.execute(
        sa.update(_Room)
        .where(sa.sql.not_(_Room.inhabitable))
        .values(address_id=_Address.id)
        .where(_Room.building_id == _Address.tmp_building_id)
    )


def add_room_addresses(session):
    room_select = (
        sa.select([_Room.id, (sa.cast(_Room.level, sa.String)
                              + "-"
                              + _Room.number).label("addition")])
        .select_from(_Room)
        .select_from(_Building)
        .where(_Building.id == _Room.building_id)
        .where(_Room.inhabitable)
        .column(_Building.street)
        .column(_Building.number)
        .column(_Building.id)
        .alias('inhabitable_room_info')
    )
    session.execute(
        sa.insert(_Address)
        .from_select([_Address.tmp_room_id, _Address.addition,
                      _Address.street, _Address.number, _Address.tmp_building_id],
                     room_select)
    )


def add_building_addresses(session):
    building_select = sa.select([_Building.street, _Building.number, _Building.id])
    session.execute(
        sa.insert(_Address)
        .from_select([_Address.street, _Address.number, _Address.tmp_building_id],
                     building_select)
        .returning(_Address.id)
    )


def add_dummy_address(session):
    # noinspection SpellCheckingInspection
    dummy_addr = _Address(street="Niemandsstraße", number="42", zip_code="33602",
                          city="Bielefeld", state="Niedersachsen")
    session.add(dummy_addr)
    session.commit()
    session.refresh(dummy_addr)
    dummy_id = dummy_addr.id
    return dummy_id


def downgrade():
    op.drop_constraint('user_address_id_fkey', 'user', type_='foreignkey')
    op.drop_index(op.f('ix_user_address_id'), table_name='user')
    op.drop_column('user', 'address_id')
    op.drop_constraint('room_address_id_fkey', 'room', type_='foreignkey')
    op.drop_index(op.f('ix_room_address_id'), table_name='room')
    op.drop_column('room', 'address_id')
    op.drop_constraint('config_dummy_address_id_fkey', 'config', type_='foreignkey')
    op.drop_column('config', 'dummy_address_id')
    op.drop_table('address')
    op.create_unique_constraint('address', 'building', ['street', 'number'])
    op.drop_constraint('building_address', 'building', type_='unique')
