# -*- coding: utf-8 -*-
from datetime import datetime, time
import ipaddr

from mysql import session as my_session, Wheim, Nutzer, Subnet, Computer

from pycroft import model
from pycroft.model import dormitory, session, port, user, host, property, logging
from pycroft.helpers.user import hash_password

def do_convert():
    houses = {}
    patch_ports = []
    switch_ports = []
    rooms = []
    switches = {}
    users = []
    ips = []
    net_devices = []

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
            new_port = port.PatchPort(name="%s/%s" % (port.etage, port.zimmernr), room=new_room)
            patch_ports.append(new_port)

            if port.ip not in switches:
                pub_ip = port.ip.replace("10.10", "141.30")
                computer = my_session.query(Computer).filter(Computer.c_ip == pub_ip).first()
                hostname = computer.c_hname
                mac = computer.c_etheraddr
                new_switch_netdevice = host.SwitchNetDevice(mac=mac)
                mgmt_ip = host.Ip(address=pub_ip, net_device=new_switch_netdevice)
                new_switch = host.Switch(name=hostname, management_ip=mgmt_ip)
                new_switch_netdevice.host = new_switch
                net_devices.append(new_switch_netdevice)
                ips.append(mgmt_ip)
                switches[port.ip] = new_switch
            new_swport = port.SwitchPort(name=port.port, switch=switches[port.ip])
            switch_ports.append(new_swport)
            new_port.destination_port = new_swport


            if int(wheim.wheim_id) == 1 and new_room.number == "41" and int(new_room.level) == 1:
                root_room = new_room


    root = user.User(login="ag_dsn", name="System User", registration_date=datetime.today(), passwd_hash=hash_password("test"))
    root.room = root_room
    for switch in switches.values():
        switch.user_id = root.id


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

    subnets = {}
    for subnet in my_session.query(Subnet):
        replaced_subnet_ip = subnet.net_ip.replace("10.10", "141.30")
        new_subnet = dormitory.Subnet(address=str(ipaddr.IPv4Network("%s/%s" % (replaced_subnet_ip, subnet.netmask))),
                                      dns_domain=subnet.domain,
                                      gateway=subnet.default_gateway,
                                      ip_type="4")
        subnets[subnet.subnet_id] = new_subnet

        vlans[subnet.vlan_name] = dormitory.VLan(name=subnet.vlan_name,
                                                 tag=vlan_tags[subnet.vlan_name])

        new_subnet.vlans.append(vlans[subnet.vlan_name])
        for house in vlan_houses[subnet.vlan_name]:
            houses[house].vlans.append(vlans[subnet.vlan_name])

    for ip in ips:
        pub_ip = ip.address.replace("10.10", "141.30")
        computer_query = my_session.query(Computer).filter(Computer.c_ip == pub_ip)
        computer = computer_query.first()
        ip.subnet = subnets[computer.c_subnet_id]


    property_groups = {"verstoß": property.PropertyGroup(name=u"Verstoß"),
                       "bewohner": property.PropertyGroup(name=u"Bewohner"),
                       "admin": property.PropertyGroup(name=u"Admin"),
                       "nutzerverwalter": property.PropertyGroup(
                           name=u"Nutzerverwalter"),
                       "finanzen": property.PropertyGroup(name=u"Finanzen"),
                       "root": property.PropertyGroup(name=u"Root"),
                       "hausmeister": property.PropertyGroup(
                           name=u"Hausmeister"),
                       "exaktiv": property.PropertyGroup(name=u"Exaktiv")}

    properties_all = [property.Property(name="no_internet",
        property_group=property_groups["verstoß"]),
                      property.Property(name="internet",
                          property_group=property_groups["bewohner"]),
                      property.Property(name="mail",
                          property_group=property_groups["bewohner"]),
                      property.Property(name="ssh_helios",
                          property_group=property_groups["bewohner"]),
                      property.Property(name="homepage_helios",
                          property_group=property_groups["bewohner"]),]


    session.session.add_all(houses.values())
    session.session.add_all(patch_ports)
    session.session.add_all(rooms)
    session.session.add_all(switches.values())
    session.session.add_all(ips)
    session.session.add_all(net_devices)
    session.session.add_all(switch_ports)
    session.session.add_all(property_groups.values())
    session.session.add_all(properties_all)
    session.session.add(root)
    session.session.add_all(subnets.values())
    session.session.add_all(vlans.values())

    logs = []
    user_hosts = []
    user_netdevices = []
    ips = []
    a_records = []
    cname_records = []

    for old_user in my_session.query(Nutzer):
        user_room = dormitory.Room.q.filter_by(
            dormitory_id=houses[old_user.wheim_id].id, level=old_user.etage,
            number=old_user.zimmernr).first()
        if old_user.status in [1,2,4,5,6,7,12]:
            if user_room is not None:
                #if user_room is None:
                #    print str(old_user.nutzer_id)+" "+str(old_user.status)+" "+str(houses[old_user.wheim_id].id)+" "+str(old_user.etage)+old_user.zimmernr
                new_user = user.User(id=old_user.nutzer_id, login=old_user.unix_account,
                    name=old_user.vname + " " + old_user.name, room_id=user_room.id
                    ,
                    registration_date=datetime.combine(old_user.anmeldedatum,time()))

                computer = my_session.query(Computer).filter(
                            Computer.nutzer_id == old_user.nutzer_id
                        ).first()

                new_host = host.UserHost(user=new_user, room=user_room)
                user_hosts.append(new_host)

                new_netdevice = host.UserNetDevice(mac=computer.c_etheraddr,
                    host=new_host)
                user_netdevices.append(new_netdevice)

                new_ip = host.Ip(address=computer.c_ip, net_device=new_netdevice,
                                subnet=subnets[computer.c_subnet_id])
                ips.append(new_ip)

                new_arecord = host.ARecord(name=computer.c_hname,
                                        address=new_ip, host=new_host)
                a_records.append(new_arecord)

                if (computer.c_alias is not None) and (len(computer.c_alias) is not 0):
                    new_cnamerecord = host.CNameRecord(name=computer.c_alias,
                                                alias_for=new_arecord, host=new_host)
                    cname_records.append(new_cnamerecord)

                if (old_user.comment is not None) and (len(old_user.comment) is not 0):
                    new_log = logging.UserLogEntry(message=u"Alte Kommentare: "+
                                                           unicode(old_user.comment,
                                                               errors="ignore"),
                        timestamp=datetime.now(), author=root, user=new_user)
                    logs.append(new_log)
                users.append(new_user)


    session.session.add_all(users)
    session.session.add_all(logs)
    session.session.add_all(user_hosts)
    session.session.add_all(user_netdevices)
    session.session.add_all(ips)
    session.session.add_all(a_records)
    session.session.add_all(cname_records)

    session.session.commit()
