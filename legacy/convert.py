# -*- coding: utf-8 -*-
from datetime import datetime, time
import ipaddr

from mysql import session as my_session, Wheim, Nutzer, Subnet, Computer

from pycroft import model
from pycroft.model import dormitory, session, port as port_model, user, host, property, logging
from pycroft.helpers.user import hash_password
from pycroft.model.dns import ARecord, CNameRecord

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
            new_port = port_model.PatchPort(name="%s/%s" % (port.etage, port.zimmernr), room=new_room)
            patch_ports.append(new_port)

            if port.ip not in switches:
                pub_ip = port.ip.replace("10.10", "141.30")
                computer = my_session.query(Computer).filter(Computer.c_ip == pub_ip).first()
                hostname = computer.c_hname
                mac = computer.c_etheraddr
                new_switch_net_device = host.SwitchNetDevice(mac=mac)
                mgmt_ip = host.Ip(address=pub_ip, net_device=new_switch_net_device)
                new_switch = host.Switch(name=hostname, management_ip=mgmt_ip.address)
                new_switch_net_device.host = new_switch
                net_devices.append(new_switch_net_device)
                ips.append(mgmt_ip)
                switches[port.ip] = new_switch
            new_swport = port_model.SwitchPort(name=port.port, switch=switches[port.ip])
            switch_ports.append(new_swport)
            new_port.destination_port = new_swport


            if int(wheim.wheim_id) == 1 and new_room.number == "41" and int(new_room.level) == 1:
                root_room = new_room

    server_room_wu5_keller = dormitory.Room(number="Keller", level="0", inhabitable=False, dormitory_id=1)
    server_room_wu9_dach = dormitory.Room(number="Dach", level="16", inhabitable=False, dormitory_id=3)
    server_room_wu11_dach = dormitory.Room(number="Dach", level="17", inhabitable=False, dormitory_id=4)
    rooms += [server_room_wu11_dach, server_room_wu5_keller, server_room_wu9_dach]

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

        vlans[subnet.vlan_name] = dormitory.VLAN(name=subnet.vlan_name,
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
                       "exaktiv": property.PropertyGroup(name=u"Exaktiv"),
                       "tmpausgezogen": property.PropertyGroup(
                           name=u"tmpAusgezogen")}

    properties_all = [property.Property(name="no_internet",
                          property_group=property_groups["verstoß"]),
                      property.Property(name="internet",
                          property_group=property_groups["bewohner"]),
                      property.Property(name="mail",
                          property_group=property_groups["bewohner"]),
                      property.Property(name="ssh_helios",
                          property_group=property_groups["bewohner"]),
                      property.Property(name="homepage_helios",
                          property_group=property_groups["bewohner"]),
                      property.Property(name="no_internet",
                          property_group=property_groups["tmpausgezogen"])]


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
    user_net_devices = []
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

                new_net_device = host.UserNetDevice(mac=computer.c_etheraddr,
                    host=new_host)
                user_net_devices.append(new_net_device)

                new_ip = host.Ip(address=computer.c_ip, net_device=new_net_device,
                                subnet=subnets[computer.c_subnet_id])
                ips.append(new_ip)

                new_a_record = ARecord(name=computer.c_hname,
                                        address=new_ip, host=new_host)
                a_records.append(new_a_record)

                if (computer.c_alias is not None) and (len(computer.c_alias) is not 0):
                    new_cname_record = CNameRecord(name=computer.c_alias,
                                                record_for=new_a_record, host=new_host)
                    cname_records.append(new_cname_record)

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
    session.session.add_all(user_net_devices)
    session.session.add_all(ips)
    session.session.add_all(a_records)
    session.session.add_all(cname_records)

    ips = []
    server_net_devices = []
    a_records = []
    server_hosts = []

    #Server
    #TODO subnet for 141.76 nets
    #Atlantis
    atlantis_net_device = host.ServerNetDevice(mac="00:e0:81:b1:3f:0e")
    server_net_devices.append(atlantis_net_device)
    atlantis_ip_1 = host.Ip(address="141.30.228.39",net_device=atlantis_net_device, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh2.tu-dresden.de").one())
    ips.append(atlantis_ip_1)
    #atlantis_ip_2 = host.Ip(address="141.76.119.130",net_device=atlantis_net_device)
    #ips.append(atlantis_ip_2)
    atlantis_host = host.ServerHost(room=server_room_wu9_dach, user=root)
    atlantis_net_device.host = atlantis_host
    server_hosts.append(atlantis_host)
    atlantis_a_record = host.ARecord(host=atlantis_host, name="atlantis.wh2.tu-dresden.de",
        address=atlantis_ip_1)
    a_records.append(atlantis_a_record)

    #Seth
    seth_net_device = host.ServerNetDevice(mac="00:04:23:8e:b9:91")
    server_net_devices.append(seth_net_device)
    seth_ip_1 = host.Ip(address="141.30.228.2",net_device=seth_net_device, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh2.tu-dresden.de").one())
    ips.append(seth_ip_1)
    #seth_ip_2 = host.Ip(address="141.76.119.134",net_device=seth_net_device)
    #ips.append(seth_ip_2)
    seth_host = host.ServerHost(room=server_room_wu5_keller, user=root)
    seth_net_device.host = seth_host
    server_hosts.append(seth_host)
    seth_a_record = host.ARecord(host=seth_host, name="seth.wh2.tu-dresden.de",
        address=seth_ip_1)
    a_records.append(seth_a_record)

    #Ramses
    ramses_net_device = host.ServerNetDevice(mac="00:04:23:9a:fe:86")
    server_net_devices.append(ramses_net_device)
    ramses_ip = host.Ip(address="141.30.228.4",net_device=ramses_net_device, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh2.tu-dresden.de").one())
    ips.append(ramses_ip)
    ramses_host = host.ServerHost(room=server_room_wu9_dach, user=root)
    ramses_net_device.host = ramses_host
    server_hosts.append(ramses_host)
    ramses_a_record = host.ARecord(host=ramses_host, name="ramses.wh2.tu-dresden.de",
        address=ramses_ip)
    a_records.append(ramses_a_record)

    #Helios
    helios_net_device = host.ServerNetDevice(mac="00:e0:81:b2:d4:b0")
    server_net_devices.append(helios_net_device)
    helios_ip = host.Ip(address="141.30.228.7",net_device=helios_net_device, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh2.tu-dresden.de").one())
    ips.append(helios_ip)
    helios_host = host.ServerHost(room=server_room_wu9_dach, user=root)
    helios_net_device.host = helios_host
    server_hosts.append(helios_host)
    helios_a_record = host.ARecord(host=helios_host, name="helios.wh2.tu-dresden.de",
        address=helios_ip)
    a_records.append(helios_a_record)

    #Gizeh
    gizeh_net_device = host.ServerNetDevice(mac="00:07:e9:10:d3:9a")
    server_net_devices.append(gizeh_net_device)
    gizeh_ip = host.Ip(address="141.30.226.4",net_device=gizeh_net_device, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh7.tu-dresden.de").one())
    ips.append(gizeh_ip)
    gizeh_host = host.ServerHost(room=server_room_wu11_dach, user=root)
    gizeh_net_device.host = gizeh_host
    server_hosts.append(gizeh_host)
    gizeh_a_record = host.ARecord(host=gizeh_host, name="gizeh.wh7.tu-dresden.de",
        address=gizeh_ip)
    a_records.append(gizeh_a_record)

    #Kerberos
    kerberos_net_device = host.ServerNetDevice(mac="00:04:23:dd:ee:e5")
    server_net_devices.append(kerberos_net_device)
    kerberos_ip = host.Ip(address="141.30.228.3",net_device=kerberos_net_device, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh2.tu-dresden.de").one())
    ips.append(kerberos_ip)
    kerberos_host = host.ServerHost(room=server_room_wu9_dach, user=root)
    kerberos_net_device.host = kerberos_host
    server_hosts.append(kerberos_host)
    kerberos_a_record = host.ARecord(host=kerberos_host, name="kerberos.wh2.tu-dresden.de",
        address=kerberos_ip)
    a_records.append(kerberos_a_record)

    #radio
    radio_net_device = host.ServerNetDevice(mac="00:16:3e:27:c0:b3")
    server_net_devices.append(radio_net_device)
    radio_ip = host.Ip(address="141.30.228.6",net_device=radio_net_device, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh2.tu-dresden.de").one())
    ips.append(radio_ip)
    radio_host = host.ServerHost(room=server_room_wu9_dach, user=root)
    radio_net_device.host = radio_host
    server_hosts.append(radio_host)
    radio_a_record = host.ARecord(host=radio_host, name="radio.wh2.tu-dresden.de",
        address=radio_ip)
    a_records.append(radio_a_record)

    #exma
    exma_net_device = host.ServerNetDevice(mac="00:16:3e:54:75:af")
    server_net_devices.append(exma_net_device)
    exma_ip = host.Ip(address="141.30.228.5",net_device=exma_net_device, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh2.tu-dresden.de").one())
    ips.append(exma_ip)
    exma_host = host.ServerHost(room=server_room_wu9_dach, user=root)
    exma_net_device.host = exma_host
    server_hosts.append(exma_host)
    exma_a_record = host.ARecord(host=exma_host, name="exma.wh2.tu-dresden.de",
        address=exma_ip)
    a_records.append(exma_a_record)

    #projecthost
    projecthost_net_device = host.ServerNetDevice(mac="00:16:3e:57:b2:25")
    server_net_devices.append(projecthost_net_device)
    projecthost_ip = host.Ip(address="141.30.228.10",net_device=projecthost_net_device, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh2.tu-dresden.de").one())
    ips.append(projecthost_ip)
    projecthost_host = host.ServerHost(room=server_room_wu9_dach, user=root)
    projecthost_net_device.host = projecthost_host
    server_hosts.append(projecthost_host)
    projecthost_a_record = host.ARecord(host=projecthost_host, name="projecthost.wh2.tu-dresden.de",
        address=projecthost_ip)
    a_records.append(projecthost_a_record)

    #linkpartner
    linkpartner_net_device = host.ServerNetDevice(mac="00:16:3e:cc:8a:f9")
    server_net_devices.append(linkpartner_net_device)
    linkpartner_ip = host.Ip(address="141.30.228.11",net_device=linkpartner_net_device, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh2.tu-dresden.de").one())
    ips.append(linkpartner_ip)
    linkpartner_host = host.ServerHost(room=server_room_wu9_dach, user=root)
    linkpartner_net_device.host = linkpartner_host
    server_hosts.append(linkpartner_host)
    linkpartner_a_record = host.ARecord(host=linkpartner_host, name="linkpartner.wh2.tu-dresden.de",
        address=linkpartner_ip)
    a_records.append(linkpartner_a_record)

    #kik
    kik_net_device = host.ServerNetDevice(mac="00:16:3e:1f:7e:25")
    server_net_devices.append(kik_net_device)
    kik_ip = host.Ip(address="141.30.228.12",net_device=kik_net_device, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh2.tu-dresden.de").one())
    ips.append(kik_ip)
    kik_host = host.ServerHost(room=server_room_wu9_dach, user=root)
    kik_net_device.host = kik_host
    server_hosts.append(kik_host)
    kik_a_record = host.ARecord(host=kik_host, name="kik.wh2.tu-dresden.de",
        address=kik_ip)
    a_records.append(kik_a_record)

    #pan
    pan_net_device_1 = host.ServerNetDevice(mac="00:0c:db:42:c4:00")
    server_net_devices.append(pan_net_device_1)
    pan_net_device_2 = host.ServerNetDevice(mac="00:0c:db:42:c4:00")
    server_net_devices.append(pan_net_device_2)
    pan_net_device_3 = host.ServerNetDevice(mac="00:0c:db:42:c4:00")
    server_net_devices.append(pan_net_device_3)
    pan_net_device_4 = host.ServerNetDevice(mac="00:0c:db:42:c4:00")
    server_net_devices.append(pan_net_device_4)
    pan_net_device_5 = host.ServerNetDevice(mac="00:0c:db:42:c4:00")
    server_net_devices.append(pan_net_device_5)
    pan_net_device_6 = host.ServerNetDevice(mac="00:0c:db:42:c4:00")
    server_net_devices.append(pan_net_device_6)
    pan_net_device_7 = host.ServerNetDevice(mac="00:0c:db:42:c4:00")
    server_net_devices.append(pan_net_device_7)
    pan_net_device_8 = host.ServerNetDevice(mac="00:0c:db:42:c4:00")
    server_net_devices.append(pan_net_device_8)
    pan_host = host.ServerHost(room=server_room_wu9_dach, user=root, name="pan")
    pan_net_device_1.host = pan_host
    pan_net_device_2.host = pan_host
    pan_net_device_3.host = pan_host
    pan_net_device_4.host = pan_host
    pan_net_device_5.host = pan_host
    pan_net_device_6.host = pan_host
    pan_net_device_7.host = pan_host
    pan_net_device_8.host = pan_host
    server_hosts.append(pan_host)
    pan_ip_1 = host.Ip(address="141.30.228.1",net_device=pan_net_device_1, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh2.tu-dresden.de").one())
    ips.append(pan_ip_1)
    pan_ip_2 = host.Ip(address="141.30.224.1",net_device=pan_net_device_2, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh6.tu-dresden.de").one())
    ips.append(pan_ip_2)
    pan_ip_3 = host.Ip(address="141.30.223.1",net_device=pan_net_device_3, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh5.tu-dresden.de").one())
    ips.append(pan_ip_3)
    pan_ip_4 = host.Ip(address="141.30.222.1",net_device=pan_net_device_4, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh4.tu-dresden.de").one())
    ips.append(pan_ip_4)
    pan_ip_5 = host.Ip(address="141.30.227.1",net_device=pan_net_device_5, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh3.tu-dresden.de").one())
    ips.append(pan_ip_5)
    pan_ip_6 = host.Ip(address="141.30.226.1",net_device=pan_net_device_6, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh7.tu-dresden.de").one())
    ips.append(pan_ip_6)
    pan_ip_7 = host.Ip(address="141.30.216.1",net_device=pan_net_device_7, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh16.tu-dresden.de").one())
    ips.append(pan_ip_7)
    pan_ip_8 = host.Ip(address="141.30.202.1",net_device=pan_net_device_8, subnet=dormitory.Subnet.q.filter(dormitory.Subnet.dns_domain == "wh30.tu-dresden.de").one())
    ips.append(pan_ip_8)
    pan_a_record_1 = host.ARecord(host=pan_host, name="pan.wh2.tu-dresden.de",
        address=pan_ip_1)
    a_records.append(pan_a_record_1)
    pan_a_record_2 = host.ARecord(host=pan_host, name="pan.wh6.tu-dresden.de",
        address=pan_ip_2)
    a_records.append(pan_a_record_2)
    pan_a_record_3 = host.ARecord(host=pan_host, name="pan.wh5.tu-dresden.de",
        address=pan_ip_3)
    a_records.append(pan_a_record_3)
    pan_a_record_4 = host.ARecord(host=pan_host, name="pan.wh4.tu-dresden.de",
        address=pan_ip_4)
    a_records.append(pan_a_record_4)
    pan_a_record_5 = host.ARecord(host=pan_host, name="pan.wh3.tu-dresden.de",
        address=pan_ip_5)
    a_records.append(pan_a_record_5)
    pan_a_record_6 = host.ARecord(host=pan_host, name="pan.wh7.tu-dresden.de",
        address=pan_ip_6)
    a_records.append(pan_a_record_6)
    pan_a_record_7 = host.ARecord(host=pan_host, name="pan.wh16.tu-dresden.de",
        address=pan_ip_7)
    a_records.append(pan_a_record_7)
    pan_a_record_8 = host.ARecord(host=pan_host, name="pan.wh30.tu-dresden.de",
        address=pan_ip_8)
    a_records.append(pan_a_record_8)

    session.session.add_all(ips)
    session.session.add_all(server_net_devices)
    session.session.add_all(a_records)
    session.session.add_all(server_hosts)



    session.session.commit()
