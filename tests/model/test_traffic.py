from datetime import timedelta, datetime

from pycroft.model import session
from pycroft.model.traffic import TrafficVolume, pmacct_traffic_egress, pmacct_traffic_ingress
from tests import FactoryDataTestBase
from tests.factories import UserWithHostFactory, IPFactory
from tests.factories.traffic import TrafficCreditFactory, TrafficVolumeFactory, \
    TrafficBalanceFactory


class PMAcctViewTest(FactoryDataTestBase):
    ip = '141.30.228.39'
    bad_ip = '141.30.228.1'
    egress_table = pmacct_traffic_egress.table
    ingress_table = pmacct_traffic_ingress.table
    def create_factories(self):
        self.user = UserWithHostFactory(host__interface__ip__str_address=self.ip)

    def build_insert(self, type, **kwargs):
        if type == 'Ingress':
            table = self.ingress_table
            ip_key = 'ip_dst'
        elif type == 'Egress':
            table = self.egress_table
            ip_key = 'ip_src'
        else:
            raise ValueError("type must be one of 'Ingress', 'Egress'")
        stamp = session.utcnow()
        values = {
            'bytes': 1024,
            'packets': 20,
            ip_key: self.ip,
            'stamp_inserted': stamp,
            'stamp_updated': stamp,
        }

        values.update(**kwargs)
        return table.insert().values(**values)

    def test_egress_insert(self):
        session.session.execute(self.build_insert(type='Egress'))
        self.assertEqual(TrafficVolume.q.count(), 1)
        volume = TrafficVolume.q.one()
        self.assertEqual(volume.type, 'Egress')
        self.assertEqual(volume.amount, 1024)
        self.assertEqual(volume.packets, 20)
        self.assertEqual(volume.user, self.user)

    def test_egress_insert_nonexistent_ip(self):
        session.session.execute(self.build_insert(type='Egress', ip_src="1.1.1.1"))
        self.assertEqual(TrafficVolume.q.count(), 0)

    def test_egress_update_successive_entries(self):
        data = [
            # timestamp, packets, amount
            ('2018-03-15 00:15:00', 200, 1024),
            ('2018-03-15 10:15:00', 324, 500),
            ('2018-03-15 23:59:00', 12, 7055),
        ]
        for stamp, packets, bytes in data:
            session.session.execute(self.build_insert(type='Egress', packets=packets, bytes=bytes,
                                                      stamp_inserted=stamp, stamp_updated=stamp))
        self.assertEqual(TrafficVolume.q.count(), 1)
        vol = TrafficVolume.q.one()
        self.assertEqual(str(vol.timestamp), '2018-03-15 00:00:00')
        self.assertEqual(vol.packets, sum(x[1] for x in data))
        self.assertEqual(vol.amount, sum(x[2] for x in data))


    def test_ingress_insert(self):
        session.session.execute(self.build_insert(type='Ingress'))
        self.assertEqual(TrafficVolume.q.count(), 1)
        volume = TrafficVolume.q.one()
        self.assertEqual(volume.type, 'Ingress')
        self.assertEqual(volume.amount, 1024)
        self.assertEqual(volume.packets, 20)
        self.assertEqual(volume.user, self.user)

    def test_ingress_insert_nonexistent_ip(self):
        session.session.execute(self.build_insert(type='Ingress', ip_dst="1.1.1.1"))
        self.assertEqual(TrafficVolume.q.count(), 0)

    def test_ingress_update_successive_entries(self):
        data = [
            # timestamp, packets, amount
            ('2018-03-15 00:15:00', 200, 1024),
            ('2018-03-15 10:15:00', 324, 500),
            ('2018-03-15 23:59:00', 12, 7055),
        ]
        for stamp, packets, bytes in data:
            session.session.execute(self.build_insert(type='Ingress', packets=packets, bytes=bytes,
                                                      stamp_inserted=stamp, stamp_updated=stamp))
        self.assertEqual(TrafficVolume.q.count(), 1)
        vol = TrafficVolume.q.one()
        self.assertEqual(str(vol.timestamp), '2018-03-15 00:00:00')
        self.assertEqual(vol.packets, sum(x[1] for x in data))
        self.assertEqual(vol.amount, sum(x[2] for x in data))


class CurrentBalanceTest(FactoryDataTestBase):
    def setUp(self, *a, **kw):
        self.now = datetime.now()
        super().setUp(*a, **kw)

    def create_factories(self):
        self.user = UserWithHostFactory()
        self.ip = self.user.hosts[0].interfaces[0].ips[0]
        for delta in range(14):
            TrafficCreditFactory.create(timestamp=self.now + timedelta(-delta),
                                        amount=3*1024**3, user=self.user)
            TrafficVolumeFactory.create(timestamp=self.now + timedelta(-delta),
                                        amount=1*1024**3, user=self.user, ip=self.ip)

        # Unrelated events should not be included in the sum
        other_user = UserWithHostFactory()
        other_ip = other_user.hosts[0].interfaces[0].ips[0]
        TrafficCreditFactory.create_batch(20, user=other_user)
        TrafficVolumeFactory.create_batch(20, user=other_user, ip=other_ip)

    def test_sum_without_balance_entry(self):
        self.assertEqual(self.user.current_credit, 28*1024**3)

    def test_sum_with_balance_entry(self):
        TrafficBalanceFactory(timestamp=self.now + timedelta(-1),
                              user=self.user, amount=2*1024**3)
        # 2GiB yesterday
        # +3GiB-1GiB yesterday and today
        self.assertEqual(self.user.current_credit, 6*1024**3)

    def test_user_without_entries_has_zero_credit(self):
        user = UserWithHostFactory()
        session.session.commit()
        self.assertEqual(user.current_credit, 0)
