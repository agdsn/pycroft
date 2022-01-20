from datetime import datetime, timedelta

from pycroft.helpers.interval import closedopen
from pycroft.model import session
from pycroft.model import hades
from pycroft.model.net import VLAN
from tests.legacy_base import FactoryDataTestBase
from tests.factories import PropertyGroupFactory, MembershipFactory, UserWithHostFactory, \
    SwitchFactory, PatchPortFactory


class HadesTestBase(FactoryDataTestBase):
    def create_factories(self):
        self.user = UserWithHostFactory.create()
        self.network_access_group = PropertyGroupFactory.create(
            name="Member",
            granted={'network_access'},
        )
        self.payment_in_default_group = PropertyGroupFactory.create(
            name="Blocked (finance)",
            granted={'payment_in_default'},
            denied={'network_access'},
        )
        self.traffic_limit_exceeded_group = PropertyGroupFactory.create(
            name="Blocked (traffic)",
            granted={'traffic_limit_exceeded'},
            denied={'network_access'},
        )

        # the user's room needs to be connected to provide `nasipaddress` and `nasportid`
        self.switch = SwitchFactory.create(host__owner=self.user)
        PatchPortFactory.create_batch(2, patched=True, switch_port__switch=self.switch,
                                      # This needs to be the HOSTS room!
                                      room=self.user.hosts[0].room)

        NOW = datetime.now()
        MembershipFactory.create(
            user=self.user, group=self.network_access_group,
            active_during=closedopen(NOW + timedelta(-1), NOW + timedelta(1))
        )

        session.session.execute(hades.radius_property.insert().values([
            ('payment_in_default',),
            ('traffic_limit_exceeded',),
        ]))


class HadesViewTest(HadesTestBase):
    def test_radcheck(self):
        # <mac> - <nasip> - <nasport> - "Cleartext-Password" - := - <mac> - 10
        # We have one interface with a MAC whose room has two ports on the same switch
        rows = session.session.query(hades.radcheck.table).all()
        host = self.user.hosts[0]
        mac = host.interfaces[0].mac
        for row in rows:
            assert row.UserName == mac
            assert row.NASIPAddress == self.switch.management_ip
            assert row.Attribute == "User-Name"
            assert row.Op == "=*"
            assert row.Value == None
            assert row.Priority == 10

        assert {row.NASPortId for row in rows} \
            == {port.switch_port.name for port in host.room.patch_ports}

    def test_radgroupcheck(self):
        rows = session.session.query(hades.radgroupcheck.table).all()
        assert len(rows) == 1
        row = rows[0]
        assert row == ("unknown", "Auth-Type", ":=", "Accept", 10)

    # Radreply is empty by default...

    def test_radgroupreply_custom_entries(self):
        radgroupreply_q = session.session.query(hades.radgroupreply.table)
        custom_reply_row = ("TestGroup", "Egress-VLAN-Name", "+=", "2Servernetz")
        assert custom_reply_row not in radgroupreply_q.all()
        session.session.execute(hades.radgroupreply_base.insert().values([custom_reply_row]))
        session.session.commit()
        assert custom_reply_row in radgroupreply_q.all()

    def test_radgroupreply_access_groups(self):
        rows = session.session.query(hades.radgroupreply.table).all()
        vlans = VLAN.q.all()
        for vlan in vlans:
            with self.subTest(vlan=vlan):
                group_name = f"{vlan.name}_untagged"
                assert (group_name, "Egress-VLAN-Name", "+=", f"2{vlan.name}") in rows
                assert (group_name, "Fall-Through", ":=", "Yes") in rows

                group_name = f"{vlan.name}_tagged"
                assert (group_name, "Egress-VLAN-Name", "+=", f"1{vlan.name}") in rows
                assert (group_name, "Fall-Through", ":=", "Yes") in rows

    def test_radgroupreply_blocking_groups(self):
        props = [x[0] for x in session.session.query(hades.radius_property).all()]
        rows = session.session.query(hades.radgroupreply.table).all()
        for prop in props:
            assert (prop, "Egress-VLAN-Name", ":=", "2hades-unauth") in rows
            assert (prop, "Fall-Through", ":=", "No") in rows

    def test_radusergroup_access(self):
        host = self.user.hosts[0]
        switch_ports = [p.switch_port for p in host.room.connected_patch_ports]
        assert len(host.ips) == 1
        assert len(host.interfaces) == 1
        mac = host.interfaces[0].mac
        group = f"{host.ips[0].subnet.vlan.name}_untagged"

        rows = session.session.query(hades.radusergroup.table).all()
        for switch_port in switch_ports:
            assert (mac, switch_port.switch.management_ip, switch_port.name, group, 20) \
                in rows

    def test_dhcphost_access(self):
        rows = session.session.query(hades.dhcphost.table).all()
        assert len(rows) == 1
        row = rows[0]
        host = self.user.hosts[0]
        assert row == (host.interfaces[0].mac, str(host.ips[0].address))


class HadesBlockedViewTest(HadesTestBase):
    def create_factories(self):
        super().create_factories()
        MembershipFactory.create(user=self.user, group=self.payment_in_default_group,
                                 begins_at=datetime.now() + timedelta(-1),
                                 ends_at=datetime.now() + timedelta(1))

    def test_radusergroup_blocked(self):
        host = self.user.hosts[0]
        switch_ports = [p.switch_port for p in host.room.connected_patch_ports]
        assert len(host.ips) == 1
        assert len(host.interfaces) == 1
        mac = host.interfaces[0].mac

        rows = session.session.query(hades.radusergroup.table).all()
        for switch_port in switch_ports:
            assert (mac, switch_port.switch.management_ip, switch_port.name,
                    'payment_in_default', -10) in rows
            assert (mac, switch_port.switch.management_ip, switch_port.name,
                    'no_network_access', 0) in rows

    def test_dhcphost_blocked(self):
        rows = session.session.query(hades.dhcphost.table).all()
        assert len(rows) == 0
