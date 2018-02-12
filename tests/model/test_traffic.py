from pycroft.model import session
from pycroft.model.traffic import TrafficVolume, pmacct_traffic_egress, pmacct_traffic_ingress
from tests import FactoryDataTestBase
from tests.factories.user import UserWithHostFactory


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
