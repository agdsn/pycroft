from sqlalchemy import literal, Column, String, BigInteger, func, union_all, Table, Integer, \
    PrimaryKeyConstraint, null, and_
from sqlalchemy.orm import Query, aliased

from pycroft.model.base import ModelBase
from pycroft.model.ddl import DDLManager, View
from pycroft.model.facilities import Room
from pycroft.model.host import Interface, Switch, SwitchPort, Host, IP
from pycroft.model.net import VLAN, Subnet
from pycroft.model.port import PatchPort
from pycroft.model.user import User
from pycroft.model.property import current_property, CurrentProperty

hades_view_ddl = DDLManager()

network_access_subq = (
    # Select `user_id, 1` for all people with network_access
    Query([current_property.table.c.user_id.label('user_id'),
           literal(1).label('network_access')])
    .filter(current_property.table.c.property_name == 'network_access')
    .subquery('users_with_network_access')
)

radius_property = Table(
    'radius_property',
    ModelBase.metadata,
    Column('property', String, primary_key=True),
)
# This is a hack to enforce that Views are created after _all_ their
# depenencies.  The Views' creation is then targeted after
# `radgroup_property_mappings`.  This would be obsolete if the
# DDLManager created Views after tables in general.
radius_property.add_is_dependent_on(Room.__table__)
radius_property.add_is_dependent_on(Interface.__table__)
radius_property.add_is_dependent_on(Switch.__table__)
radius_property.add_is_dependent_on(SwitchPort.__table__)
radius_property.add_is_dependent_on(PatchPort.__table__)
radius_property.add_is_dependent_on(Host.__table__)
radius_property.add_is_dependent_on(VLAN.__table__)
radius_property.add_is_dependent_on(Subnet.__table__)
radius_property.add_is_dependent_on(User.__table__)

radusergroup = View(
    name='radusergroup',
    query=union_all(
        # Priority 20: valid case (interface's mac w/ vlan at correct ports)
        # <mac> @ <switch>/<port> → <vlan>_[un]tagged (Prio 20)
        # Parsing continues because of Fall-Through:=Yes
        Query([
            Interface.mac.label('UserName'),
            # `host()` does not print the `/32` like `text` would
            func.host(Switch.management_ip).label('NASIPAddress'),
            SwitchPort.name.label('NASPortId'),
            # TODO: add `_tagged` instead if interface needs that
            (VLAN.name + '_untagged').label('GroupName'),
            literal(20).label('Priority'),
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

        # Priority -10: Blocking reason exists
        # <mac> @ <switch>/<port> → <blocking_group> (Prio -10)
        # Note that Fall-Through:=No for blocking groups, so first match terminates
        Query([
            Interface.mac.label('UserName'),
            func.host(Switch.management_ip).label('NASIPAddress'),
            SwitchPort.name.label('NASPortId'),
            radius_property.c.property.label('GroupName'),
            literal(-10).label('Priority'),
        ]).select_from(User)
        .join(Host)
        .join(Host.interfaces)
        .join(Host.room)
        .join(Room.connected_patch_ports)
        .join(SwitchPort)
        .join(Switch)
        .join(current_property.table, current_property.table.c.user_id == User.id)
        .join(radius_property,
              radius_property.c.property == current_property.table.c.property_name)
        .statement,

        # Priority 0: No blocking reason exists → generic error group `no_network_access`
        Query([
            Interface.mac.label('UserName'),
            func.host(Switch.management_ip).label('NASIPAddress'),
            SwitchPort.name.label('NASPortId'),
            literal('no_network_access').label('GroupName'),
            literal(0).label('Priority'),
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
hades_view_ddl.add_view(radius_property, radusergroup)

radcheck = View(
    name='radcheck',
    query=(
        # This adds all existing interfaces.
        Query([
            func.text(Interface.mac).label('UserName'),
            func.host(Switch.management_ip).label('NASIPAddress'),
            SwitchPort.name.label('NASPortId'),
            literal("User-Name").label('Attribute'),
            literal("=*").label('Op'),
            null().label('Value'),
            literal(10).label('Priority'),
        ]).select_from(Interface)
        .join(Host)
        .join(Room)
        .join(Room.connected_patch_ports)
        .join(SwitchPort)
        .join(Switch)
        .statement
    ),
)
hades_view_ddl.add_view(radius_property, radcheck)

radgroupcheck = View(
    name='radgroupcheck',
    query=Query([
        literal("unknown").label('GroupName'),
        literal("Auth-Type").label('Attribute'),
        literal(":=").label('Op'),
        literal("Accept").label('Value'),
        literal(10).label('Priority'),
    ]).statement,
)
hades_view_ddl.add_view(radius_property, radgroupcheck)

radreply = Table(
    'radreply',
    ModelBase.metadata,
    Column('Priority', Integer),
    Column('UserName', String(64), nullable=False),
    Column('NASIPAddress', String(15), nullable=False),
    Column('NASPortId', String(50), nullable=False),
    Column('Attribute', String(64), nullable=False),
    Column('Op', String(2), nullable=False),
    Column('Value', String(253), nullable=False),
    PrimaryKeyConstraint('UserName', 'NASIPAddress', 'NASPortId', 'Priority'),
)

radgroupreply_base = Table(
    'radgroupreply_base',
    ModelBase.metadata,
    Column('GroupName', String),
    Column('Attribute', String),
    Column('Op', String),
    Column('Value', String),
    PrimaryKeyConstraint('GroupName', 'Attribute', 'Op', 'Value'),
)

radgroupreply = View(
    name='radgroupreply',
    query=union_all(
        Query([
            radgroupreply_base.c.GroupName.label('GroupName'),
            radgroupreply_base.c.Attribute.label('Attribute'),
            radgroupreply_base.c.Op.label('Op'),
            radgroupreply_base.c.Value.label('Value'),
        ]),
        # Egress-VLAN-Name += <vlan>, non-blocking groups
        Query([
            (VLAN.name + '_untagged').label('GroupName'),
            literal("Egress-VLAN-Name").label('Attribute'),
            literal('+=').label('Op'),
            (literal('2') + VLAN.name).label('Value'),
        ]),
        Query([
            (VLAN.name + '_tagged').label('GroupName'),
            literal("Egress-VLAN-Name").label('Attribute'),
            literal('+=').label('Op'),
            (literal('1') + VLAN.name).label('Value'),
        ]),
        # Fall-Through := Yes, non-blocking groups
        Query([
            (VLAN.name + '_untagged').label('GroupName'),
            literal("Fall-Through").label('Attribute'),
            literal(':=').label('Op'),
            literal('Yes').label('Value'),
        ]),
        Query([
            (VLAN.name + '_tagged').label('GroupName'),
            literal("Fall-Through").label('Attribute'),
            literal(':=').label('Op'),
            literal('Yes').label('Value'),
        ]),
        # Egress-VLAN-Name := 2hades-unauth, blocking groups
        Query([
            radius_property.c.property.label('GroupName'),
            literal("Egress-VLAN-Name").label('Attribute'),
            literal(":=").label('Op'),
            literal("2hades-unauth").label('Value'),
        ]),
        # Fall-Through := No, blocking groups
        Query([
            radius_property.c.property.label('GroupName'),
            literal("Fall-Through").label('Attribute'),
            literal(":=").label('Op'),
            literal("No").label('Value'),
        ]),
        # Generic error group `no_network_access`
        # Same semantics as a specific error group
        Query([
            literal("no_network_access").label('GroupName'),
            literal("Egress-VLAN-Name").label('Attribute'),
            literal(":=").label('Op'),
            literal("2hades-unauth").label('Value'),
        ]),
        Query([
            literal("no_network_access").label('GroupName'),
            literal("Fall-Through").label('Attribute'),
            literal(":=").label('Op'),
            literal("No").label('Value'),
        ]),
    ),
)

hades_view_ddl.add_view(radius_property, radgroupreply)

nas = Table(
    'nas',
    ModelBase.metadata,
    Column('Id', Integer, primary_key=True),
    Column('NASName', String(128), nullable=False, unique=True),
    Column('ShortName', String(32), nullable=False),
    Column('Type', String(30), nullable=False, default='other'),
    Column('Ports', Integer),
    Column('Secret', String(60), nullable=False),
    Column('Server', String(64)),
    Column('Community', String(50)),
    Column('Description', String(200)),
)


dhcphost = View(
    name='dhcphost',
    query=(
        Query([Interface.mac.label('Mac'), func.host(IP.address).label('IpAddress')])
        .select_from(User)
        .join(User._current_properties)
        .join(Host)
        .join(Interface)
        .join(IP)
        .filter(CurrentProperty.property_name == 'network_access')
        .statement
    ),
)
hades_view_ddl.add_view(ModelBase.metadata, dhcphost)

current_prop_alias = aliased(CurrentProperty)
alternative_dns = View(
    name='alternative_dns',
    query=(
        Query([func.host(IP.address).label('IpAddress')])
        .select_from(User)
        .join(Host)
        .join(Interface)
        .join(IP)
        .join(CurrentProperty, and_(CurrentProperty.user_id == User.id,
                                    CurrentProperty.property_name == 'network_access'))
        .join(current_prop_alias, and_(current_prop_alias.user_id == User.id,
                                       current_prop_alias.property_name == 'cache_access'))
        .statement
    ),
)
hades_view_ddl.add_view(ModelBase.metadata, alternative_dns)

hades_view_ddl.register()
