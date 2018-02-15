from sqlalchemy import literal, Column, String, BigInteger, func
from sqlalchemy.orm import Query

from pycroft.model.base import ModelBase
from pycroft.model.ddl import DDLManager, View
from pycroft.model.facilities import Room
from pycroft.model.host import Interface, Switch, SwitchPort, Host

hades_view_ddl = DDLManager()

radusergroup = View(
    name='radusergroup',
    metadata=ModelBase.metadata,
    query=(
        # This adds all existing interfaces.
        Query([]).add_columns(
            Interface.mac.label('username'),
            # `host()` does not print the `/32` like `text` would
            func.host(Switch.management_ip).label('nasipaddress'),
            SwitchPort.name.label('nasportid'),
            # testgroup and priority have dummy values atm
            literal("testgroup").label('groupname'),
            literal(0).label('priority'),
        ).select_from(Interface)
         .join(Host)
         .join(Room)
         .join(Room.connected_patch_ports)
         .join(SwitchPort)
         .join(Switch)
         .statement
    ),
)

radcheck = View(
    name='radcheck',
    metadata=ModelBase.metadata,
    query=(
        # This adds all existing interfaces.
        Query([]).add_columns(
            Interface.id.label('id'),
            func.text(Interface.mac).label('username'),
            func.host(Switch.management_ip).label('nasipaddress'),
            SwitchPort.name.label('nasportid'),
            literal("Cleartext-Password").label('attribute'),
            literal(":=").label('op'),
            func.text(Interface.mac).label('value'),
        ).select_from(Interface)
         .join(Host)
         .join(Room)
         .join(Room.connected_patch_ports)
         .join(SwitchPort)
         .join(Switch)
         .statement
    ),
)
