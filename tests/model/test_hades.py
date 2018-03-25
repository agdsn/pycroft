from datetime import datetime, timedelta

from pycroft.model import session
from pycroft.model.hades import radgroup_property_mappings, radcheck
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
        self.blocked_by_finance_group = PropertyGroupFactory.create(
            name="Blocked (finance)",
            granted={'blocked_by_finance'},
            denied={'network_access'},
        )
        self.blocked_by_traffic_group = PropertyGroupFactory.create(
            name="Blocked (traffic)",
            granted={'blocked_by_traffic'},
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
        MembershipFactory.create(user=self.user, group=self.blocked_by_finance_group,
                                 begins_at=datetime.now() + timedelta(-1),
                                 ends_at=datetime.now() + timedelta(1))

        session.session.execute(radgroup_property_mappings.insert(values=[
            {'property': 'blocked_by_finance', 'radgroup': 'finance'},
            {'property': 'blocked_by_traffic', 'radgroup': 'traffic'},
        ]))

    def test_radcheck(self):
        # <mac> - <nasip> - <nasport> - "Cleartext-Password" - := - <mac> - 10
        # We have one interface with a MAC whose room has two ports on the same switch
        rows = session.session.query(radcheck.table).all()
        host = self.user.hosts[0]
        mac = host.interfaces[0].mac
        for row in rows:
            self.assertEqual(row.username, mac)
            self.assertEqual(row.nasipaddress, self.switch.management_ip)
            self.assertEqual(row.attribute, "Cleartext-Password")
            self.assertEqual(row.op, ":=")
            self.assertEqual(row.value, mac)
            self.assertEqual(row.priority, 10)

        self.assertEqual({row.nasportid for row in rows},
                         {port.switch_port.name for port in host.room.patch_ports})

    # TODO: Put Entries in some basetable to test tagged vlans (separate test)
    # TODO: test radreply, radgroupreply (with base, see above), radgroupcheck
