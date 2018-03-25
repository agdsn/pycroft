from sqlalchemy import literal, Column, String, BigInteger, func, union_all, Table, Integer, \
    PrimaryKeyConstraint
from sqlalchemy.orm import Query

from pycroft.model.base import ModelBase
from pycroft.model.ddl import DDLManager, View
from pycroft.model.facilities import Room
from pycroft.model.host import Interface, Switch, SwitchPort, Host
from pycroft.model.net import VLAN, Subnet
from pycroft.model.port import PatchPort
from pycroft.model.user import User
from pycroft.model.property import current_property

hades_view_ddl = DDLManager()

network_access_subq = (
    # Select `user_id, 1` for all people with network_access
    Query([current_property.table.c.user_id.label('user_id'),
           literal(1).label('network_access')])
    .filter(current_property.table.c.property_name == 'network_access')
    .subquery('users_with_network_access')
)

radgroup_property_mappings = Table(
    'radgroup_property_mappings',
    ModelBase.metadata,
    Column('property', String, primary_key=True),
    Column('radgroup', String(128), nullable=False),
)
# This is a hack to enforce that Views are created after _all_ their
# depenencies.  The Views' creation is then targeted after
# `radgroup_property_mappings`.  This would be obsolete if the
# DDLManager created Views after tables in general.
radgroup_property_mappings.add_is_dependent_on(Room.__table__)
radgroup_property_mappings.add_is_dependent_on(Interface.__table__)
radgroup_property_mappings.add_is_dependent_on(Switch.__table__)
radgroup_property_mappings.add_is_dependent_on(SwitchPort.__table__)
radgroup_property_mappings.add_is_dependent_on(PatchPort.__table__)
radgroup_property_mappings.add_is_dependent_on(Host.__table__)
radgroup_property_mappings.add_is_dependent_on(VLAN.__table__)
radgroup_property_mappings.add_is_dependent_on(Subnet.__table__)
radgroup_property_mappings.add_is_dependent_on(User.__table__)

radusergroup = View(
    name='radusergroup',
    query=union_all(
        # Priority 20: valid case (interface's mac w/ vlan at correct ports)
        # <mac> @ <switch>/<port> → <vlan>_[un]tagged (Prio 20)
        Query([
            Interface.mac.label('username'),
            # `host()` does not print the `/32` like `text` would
            func.host(Switch.management_ip).label('nasipaddress'),
            SwitchPort.name.label('nasportid'),
            # TODO: add `_tagged` instead if interface needs that
            (VLAN.name + '_untagged').label('groupname'),
            literal(20).label('priority'),
        ]).select_from(User)
        .join(Host)
        .join(Interface)
        .join(Host.room)
        .join(Room.connected_patch_ports)
        .join(SwitchPort)
        .join(Switch)
        .join(Interface.ips)
        .join(Subnet)
        .join(VLAN)
        .join(current_property.table, current_property.table.c.user_id == User.id)
        .filter(current_property.table.c.property_name == 'network_access')
        .statement,

        # Priority 10: Blocking reason exists
        # <mac> @ <switch>/<port> → finance (Prio 10)
        Query([
            Interface.mac.label('username'),
            func.host(Switch.management_ip).label('nasipaddress'),
            SwitchPort.name.label('nasportid'),
            radgroup_property_mappings.c.radgroup.label('groupname'),
            literal(10).label('priority'),
        ]).select_from(User)
        .join(Host)
        .join(Host.interfaces)
        .join(Host.room)
        .join(Room.connected_patch_ports)
        .join(SwitchPort)
        .join(Switch)
        .join(current_property.table, current_property.table.c.user_id == User.id)
        .join(radgroup_property_mappings,
              radgroup_property_mappings.c.property == current_property.table.c.property_name)
        .statement,

        # Priority 0: No blocking reason exists → assume no member (yet/anymore)
        Query([
            Interface.mac.label('username'),
            func.host(Switch.management_ip).label('nasipaddress'),
            SwitchPort.name.label('nasportid'),
            literal('no_member').label('groupname'),
            literal(0).label('priority'),
        ]).select_from(User)
        .outerjoin(network_access_subq, User.id == network_access_subq.c.user_id)
        .filter(network_access_subq.c.network_access == None)
        .join(User.hosts)
        .join(Host.interfaces)
        .join(Host.room)
        .join(Room.connected_patch_ports)
        .join(SwitchPort)
        .join(Switch)
        .statement,
    ),
)
hades_view_ddl.add_view(radgroup_property_mappings, radusergroup)

radcheck = View(
    name='radcheck',
    query=(
        # This adds all existing interfaces.
        Query([
            func.text(Interface.mac).label('username'),
            func.host(Switch.management_ip).label('nasipaddress'),
            SwitchPort.name.label('nasportid'),
            literal("Cleartext-Password").label('attribute'),
            literal(":=").label('op'),
            func.text(Interface.mac).label('value'),
            literal(10).label('priority'),
        ]).select_from(Interface)
        .join(Host)
        .join(Room)
        .join(Room.connected_patch_ports)
        .join(SwitchPort)
        .join(Switch)
        .statement
    ),
)
hades_view_ddl.add_view(radgroup_property_mappings, radcheck)

radgroupcheck = View(
    name='radgroupcheck',
    query=Query([
        literal("unknown").label('groupname'),
        literal("Auth-Type").label('attribute'),
        literal(":=").label('op'),
        literal("Accept").label('value'),
        literal(10).label('priority'),
    ]).statement,
)
hades_view_ddl.add_view(radgroup_property_mappings, radgroupcheck)

radreply = Table(
    'radreply',
    ModelBase.metadata,
    Column('priority', Integer),
    Column('username', String(64), nullable=False),
    Column('nasipaddress', String(15), nullable=False),
    Column('nasportid', String(50), nullable=False),
    Column('attribute', String(64), nullable=False),
    Column('op', String(2), nullable=False),
    Column('value', String(253), nullable=False),
    PrimaryKeyConstraint('username', 'nasipaddress', 'nasportid', 'priority'),
)

radgroupreply_base = Table(
    'radgroupreply_base',
    ModelBase.metadata,
    Column('groupname', String),
    Column('attribute', String),
    Column('op', String),
    Column('value', String),
    PrimaryKeyConstraint('groupname', 'attribute', 'op', 'value'),
)

radgroupreply = View(
    name='radgroupreply',
    query=union_all(
        Query([
            radgroupreply_base.c.groupname.label('groupname'),
            radgroupreply_base.c.attribute.label('attribute'),
            radgroupreply_base.c.op.label('op'),
            radgroupreply_base.c.value.label('value'),
        ]),
        Query([
            (VLAN.name + '_untagged').label('groupname'),
            literal("Egress-VLAN-Name").label('attribute'),
            literal('+=').label('op'),
            (literal('2') + VLAN.name).label('value'),
        ]),
        Query([
            (VLAN.name + '_tagged').label('groupname'),
            literal("Egress-VLAN-Name").label('attribute'),
            literal('+=').label('op'),
            (literal('1') + VLAN.name).label('value'),
        ]),
        Query([
            (VLAN.name + '_untagged').label('groupname'),
            literal("Reply-Message").label('attribute'),
            literal('+=').label('op'),
            (VLAN.name + '_untagged').label('value'),
        ]),
        Query([
            (VLAN.name + '_tagged').label('groupname'),
            literal("Reply-Message").label('attribute'),
            literal('+=').label('op'),
            (VLAN.name + '_tagged').label('value'),
        ]),
    ),
)
hades_view_ddl.add_view(radgroup_property_mappings, radgroupreply)

nas = Table(
    'nas',
    ModelBase.metadata,
    Column('id', Integer, primary_key=True),
    Column('nasname', String(128), nullable=False, unique=True),
    Column('shortname', String(32), nullable=False),
    Column('type', String(30), nullable=False, default='other'),
    Column('ports', Integer),
    Column('secret', String(60), nullable=False),
    Column('server', String(64)),
    Column('community', String(50)),
    Column('description', String(200)),
)

hades_view_ddl.register()
