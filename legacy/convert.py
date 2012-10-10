
from datetime import datetime
import ipaddr

from mysql import session as my_session, Wheim, Nutzer, Subnet, Computer

from pycroft import model
from pycroft.model import dormitory, session, ports, user, hosts

def do_convert():
    houses = {}
    patch_ports = []
    switch_ports = []
    rooms = []
    switches = {}

    root_room = None

    for wheim in my_session.query(Wheim):
        new_house = dormitory.Dormitory(number=wheim.hausnr, short_name = wheim.kuerzel, street=wheim.str)
        houses[wheim.wheim_id] = new_house

        for port in wheim.port_qry():
            new_room = dormitory.Room.q.filter_by(number=port.zimmernr,
                level=port.etage,
                dormitory=new_house).first()
            if new_room is None:
                new_room = dormitory.Room(number=port.zimmernr, level=port.etage, inhabitable=True, dormitory=new_house)
                rooms.append(new_room)
            new_port = ports.PatchPort(name="%s/%s" % (port.etage, port.zimmernr), room=new_room)
            patch_ports.append(new_port)

            if port.ip not in switches:
                pub_ip = port.ip.replace("10.10", "141.30")
                hostname = my_session.query(Computer.c_hname.label("hname")).filter(Computer.c_ip == pub_ip).first().hname
                new_switch = hosts.Switch(hostname=port.ip.split(".")[3], name=hostname, management_ip=port.ip)
                switches[port.ip] = new_switch
            new_swport = ports.SwitchPort(name=port.port, switch=switches[port.ip])
            switch_ports.append(new_swport)
            new_port.destination_port = new_swport


            if int(wheim.wheim_id) == 1 and new_room.number == "41" and int(new_room.level) == 1:
                root_room = new_room


    root = user.User(login="ag_dsn", name="System User", registration_date=datetime.today())
    root.room = root_room
    for switch in switches.values():
        switch.user = root


    vlan_houses = {'Wu1': (5,),
                   'Wu3': (6,),
                   'Wu7': (2,),
                   'Wu11': (4,),
                   'ZellescherWeg': (7,8,9,10,11),
                   'Wu5': (1,),
                   'Wu9': (3,),
                   'UNEPWeb': (10,)}

    vlan_tags = {'Wu1': 11,
                 'Wu3': 13,
                 'Wu7': 17,
                 'Wu11': 5,
                 'ZellescherWeg': 41,
                 'Wu5': 15,
                 'Wu9': 19,
                 'UNEPWeb': 348}

    vlans = {}

    subnets = []
    for subnet in my_session.query(Subnet):
        new_subnet = dormitory.Subnet(address=str(ipaddr.IPv4Network("%s/%s" % (subnet.net_ip, subnet.netmask))),
                                      dns_domain=subnet.domain,
                                      gateway=subnet.default_gateway)
        subnets.append(new_subnet)

        vlans[subnet.vlan_name] = dormitory.VLan(name=subnet.vlan_name,
                                                 tag=vlan_tags[subnet.vlan_name])

        new_subnet.vlans.append(vlans[subnet.vlan_name])
        for house in vlan_houses[subnet.vlan_name]:
            houses[house].vlans.append(vlans[subnet.vlan_name])


    session.session.add_all(houses.values())
    session.session.add_all(patch_ports)
    session.session.add_all(rooms)
    session.session.add_all(switches.values())
    session.session.add_all(switch_ports)
    session.session.add(root)
    session.session.add_all(subnets)
    session.session.add_all(vlans.values())

    session.session.commit()
