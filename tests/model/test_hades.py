from datetime import datetime, timedelta

import pytest

from pycroft.helpers.interval import closedopen
from pycroft.model import hades
from pycroft.model.net import VLAN
from tests.factories import PropertyGroupFactory, MembershipFactory, \
    SwitchFactory, PatchPortFactory, UserFactory


@pytest.fixture(scope='module', autouse=True)
def network_access_group(module_session):
    return PropertyGroupFactory.create(
        name="Member",
        granted={'network_access'},
    )


@pytest.fixture(scope='module', autouse=True)
def payment_in_default_group(module_session):
    return PropertyGroupFactory.create(
        name="Blocked (finance)",
        granted={'payment_in_default'},
        denied={'network_access'},
    )


@pytest.fixture(scope='module', autouse=True)
def traffic_limit_exceeded_group(module_session):
    return PropertyGroupFactory.create(
        name="Blocked (traffic)",
        granted={'traffic_limit_exceeded'},
        denied={'network_access'},
    )


@pytest.fixture(scope='module', autouse=True)
def user(module_session):
    return UserFactory(with_host=True)


@pytest.fixture(scope='module', autouse=True)
def switch(module_session, user):
    # the user's room needs to be connected to provide `nasipaddress` and `nasportid`
    switch = SwitchFactory.create(host__owner=user)
    PatchPortFactory.create_batch(
        2, patched=True, switch_port__switch=switch,
        # This needs to be the HOSTS room!
        room=user.hosts[0].room
    )
    return switch


@pytest.fixture(scope='module')
def now():
    return datetime.now()


@pytest.fixture(scope='module', autouse=True)
def membership(module_session, user, network_access_group, now):
    return MembershipFactory.create(
        user=user, group=network_access_group,
        active_during=closedopen(now + timedelta(-1), now + timedelta(1))
    )


@pytest.fixture(scope='module', autouse=True)
def mapped_radius_properties(module_session):
    module_session.execute(hades.radius_property.insert().values([
        ('payment_in_default',),
        ('traffic_limit_exceeded',),
    ]))


class TestHadesView:
    def test_radcheck(self, session, user, switch):
        # <mac> - <nasip> - <nasport> - "Cleartext-Password" - := - <mac> - 10
        # We have one interface with a MAC whose room has two ports on the same switch
        rows = session.query(hades.radcheck.table).all()
        host = user.hosts[0]
        mac = host.interfaces[0].mac
        for row in rows:
            assert row.UserName == mac
            assert row.NASIPAddress == switch.management_ip
            assert row.Attribute == "User-Name"
            assert row.Op == "=*"
            assert row.Value is None
            assert row.Priority == 10

        assert {row.NASPortId for row in rows} \
            == {port.switch_port.name for port in host.room.patch_ports}

    def test_radgroupcheck(self, session):
        rows = session.query(hades.radgroupcheck.table).all()
        assert len(rows) == 1
        row = rows[0]
        assert row == ("unknown", "Auth-Type", ":=", "Accept", 10)

    # Radreply is empty by default...

    def test_radgroupreply_custom_entries(self, session):
        radgroupreply_q = session.query(hades.radgroupreply.table)
        custom_reply_row = ("TestGroup", "Egress-VLAN-Name", "+=", "2Servernetz")
        assert custom_reply_row not in radgroupreply_q.all()
        session.execute(hades.radgroupreply_base.insert().values([custom_reply_row]))
        session.flush()
        assert custom_reply_row in radgroupreply_q.all()

    def test_radgroupreply_access_groups(self, session):
        rows = session.query(hades.radgroupreply.table).all()
        vlans = VLAN.q.all()
        for vlan in vlans:
            # TODO properly parametrize this
            group_name = f"{vlan.name}_untagged"
            assert (group_name, "Egress-VLAN-Name", "+=", f"2{vlan.name}") in rows
            assert (group_name, "Fall-Through", ":=", "Yes") in rows

            group_name = f"{vlan.name}_tagged"
            assert (group_name, "Egress-VLAN-Name", "+=", f"1{vlan.name}") in rows
            assert (group_name, "Fall-Through", ":=", "Yes") in rows

    def test_radgroupreply_blocking_groups(self, session):
        props = [x[0] for x in session.query(hades.radius_property).all()]
        rows = session.query(hades.radgroupreply.table).all()
        for prop in props:
            assert (prop, "Egress-VLAN-Name", ":=", "2hades-unauth") in rows
            assert (prop, "Fall-Through", ":=", "No") in rows

    def test_radusergroup_access(self, session, user):
        host = user.hosts[0]
        switch_ports = [p.switch_port for p in host.room.connected_patch_ports]
        assert len(host.ips) == 1
        assert len(host.interfaces) == 1
        mac = host.interfaces[0].mac
        group = f"{host.ips[0].subnet.vlan.name}_untagged"

        rows = session.query(hades.radusergroup.table).all()
        for switch_port in switch_ports:
            assert (mac, str(switch_port.switch.management_ip), switch_port.name, group, 20) \
                in rows

    def test_dhcphost_access(self, session, user):
        rows = session.query(hades.dhcphost.table).all()
        assert len(rows) == 1
        row = rows[0]
        host = user.hosts[0]
        assert row == (host.interfaces[0].mac, str(host.ips[0].address), host.name)


class TestHadesBlockedView:
    @pytest.fixture(scope='class', autouse=True)
    def payment_in_default_membership(self, now, class_session, user, payment_in_default_group):
        return MembershipFactory.create(
            user=user, group=payment_in_default_group,
            begins_at=now + timedelta(-1),
            ends_at=now + timedelta(1)
        )

    def test_radusergroup_blocked(self, session, user):
        host = user.hosts[0]
        switch_ports = [p.switch_port for p in host.room.connected_patch_ports]
        assert len(host.ips) == 1
        assert len(host.interfaces) == 1
        mac = host.interfaces[0].mac

        rows = session.query(hades.radusergroup.table).all()
        for switch_port in switch_ports:
            assert (mac, str(switch_port.switch.management_ip), switch_port.name,
                    'payment_in_default', -10) in rows
            assert (mac, str(switch_port.switch.management_ip), switch_port.name,
                    'no_network_access', 0) in rows

    def test_dhcphost_blocked(self, session):
        rows = session.query(hades.dhcphost.table).all()
        assert len(rows) == 0
