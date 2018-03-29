from datetime import datetime, timedelta

from pycroft.model import session
from pycroft.model.hades import radius_property, radcheck
from tests import FactoryDataTestBase
from tests.factories import PropertyGroupFactory, MembershipFactory, UserWithHostFactory, \
    SwitchFactory, PatchPortFactory


class HadesViewTest(FactoryDataTestBase):
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
        # TODO: remove owner and see if things still work
        self.switch = SwitchFactory.create(host__owner=self.user)
        PatchPortFactory.create_batch(2, patched=True, switch_port__switch=self.switch,
                                      # This needs to be the HOSTS room!
                                      room=self.user.hosts[0].room)

        # TODO: create this membership in each test, not here
        MembershipFactory.create(user=self.user, group=self.network_access_group,
                                 begins_at=datetime.now() + timedelta(-1),
                                 ends_at=datetime.now() + timedelta(1))
        MembershipFactory.create(user=self.user, group=self.payment_in_default_group,
                                 begins_at=datetime.now() + timedelta(-1),
                                 ends_at=datetime.now() + timedelta(1))

        session.session.execute(radius_property.insert(values=[
            ('payment_in_default',),
            ('traffic_limit_exceeded',),
        ]))

    def test_radcheck(self):
        # <mac> - <nasip> - <nasport> - "Cleartext-Password" - := - <mac> - 10
        # We have one interface with a MAC whose room has two ports on the same switch
        rows = session.session.query(radcheck.table).all()
        host = self.user.hosts[0]
        mac = host.interfaces[0].mac
        for row in rows:
            self.assertEqual(row.UserName, mac)
            self.assertEqual(row.NASIPAddress, self.switch.management_ip)
            self.assertEqual(row.Attribute, "User-Name")
            self.assertEqual(row.Op, "=*")
            self.assertEqual(row.Value, None)
            self.assertEqual(row.Priority, 10)

        self.assertEqual({row.NASPortId for row in rows},
                         {port.switch_port.name for port in host.room.patch_ports})

    # TODO: Put Entries in some basetable to test tagged vlans (separate test)
    # TODO: test radreply, radgroupreply (with base, see above), radgroupcheck
