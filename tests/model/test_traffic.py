import pytest

from pycroft.model.traffic import TrafficVolume, pmacct_traffic_egress, \
    pmacct_traffic_ingress, TrafficDirection
from tests.factories import UserFactory

ip = '141.30.228.39'
bad_ip = '141.30.228.1'
egress_table = pmacct_traffic_egress.table
ingress_table = pmacct_traffic_ingress.table


@pytest.fixture(scope='module')
def user(module_session):
    return UserFactory(with_host=True, host__interface__ip__str_address=ip)


def traffic_insert(stamp, table, ip_key, **kwargs):
    return table.insert().values(**{
        'bytes': 1024,
        'packets': 20,
        ip_key: ip,
        'stamp_inserted': stamp,
        'stamp_updated': stamp,
        **kwargs
    })


def egress_insert(stamp, **kwargs):
    return traffic_insert(stamp, table=egress_table, ip_key='ip_src', **kwargs)


def ingress_insert(stamp, **kwargs):
    return traffic_insert(stamp, table=ingress_table, ip_key='ip_dst', **kwargs)


class TestPMAcctView:
    def test_egress_insert(self, user, session, utcnow):
        session.execute(egress_insert(utcnow))
        assert TrafficVolume.q.count() == 1
        volume = TrafficVolume.q.one()
        assert volume.type == TrafficDirection.Egress
        assert volume.amount == 1024
        assert volume.packets == 20
        assert volume.user == user

    def test_egress_insert_nonexistent_ip(self, session, utcnow):
        session.execute(egress_insert(utcnow, ip_src="1.1.1.1"))
        assert TrafficVolume.q.count() == 0

    def test_egress_update_successive_entries(self, session, utcnow):
        data = [
            # timestamp, packets, amount
            ('2018-03-15 00:15:00', 200, 1024),
            ('2018-03-15 10:15:00', 324, 500),
            ('2018-03-15 23:59:00', 12, 7055),
        ]
        for stamp, packets, bytes in data:
            session.execute(egress_insert(
                utcnow, packets=packets, bytes=bytes,
                stamp_inserted=stamp, stamp_updated=stamp
            ))
        assert TrafficVolume.q.count() == 1
        vol = TrafficVolume.q.one()
        assert str(vol.timestamp) == '2018-03-15 00:00:00+00:00'
        assert vol.packets == sum(x[1] for x in data)
        assert vol.amount == sum(x[2] for x in data)

    def test_ingress_insert(self, user, session, utcnow):
        session.execute(ingress_insert(utcnow))
        assert TrafficVolume.q.count() == 1
        volume = TrafficVolume.q.one()
        assert volume.type == TrafficDirection.Ingress
        assert volume.amount == 1024
        assert volume.packets == 20
        assert volume.user == user

    def test_ingress_insert_nonexistent_ip(self, session, utcnow):
        session.execute(ingress_insert(utcnow, ip_dst="1.1.1.1"))
        assert TrafficVolume.q.count() == 0

    def test_ingress_update_successive_entries(self, session, utcnow):
        data = [
            # timestamp, packets, amount
            ('2018-03-15 00:15:00', 200, 1024),
            ('2018-03-15 10:15:00', 324, 500),
            ('2018-03-15 23:59:00', 12, 7055),
        ]
        for stamp, packets, bytes in data:
            session.execute(ingress_insert(
                utcnow, packets=packets, bytes=bytes,
                stamp_inserted=stamp, stamp_updated=stamp
            ))
        assert TrafficVolume.q.count() == 1
        vol = TrafficVolume.q.one()
        assert str(vol.timestamp) == '2018-03-15 00:00:00+00:00'
        assert vol.packets == sum(x[1] for x in data)
        assert vol.amount == sum(x[2] for x in data)
