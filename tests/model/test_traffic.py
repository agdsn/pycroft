from pycroft.model.traffic import PmacctTrafficEgress, PmacctTrafficIngress, TrafficVolume
from tests import FactoryDataTestBase
from tests.factories.traffic import PMAcctTrafficEgressFactory, PMAcctTrafficIngressFactory
from tests.factories.user import UserWithHostFactory


class PMAcctPseudoTableTest(FactoryDataTestBase):
    ip = '141.30.228.39'
    bad_ip = '141.30.228.1'
    def create_factories(self):
        self.user = UserWithHostFactory(host__interface__ip__str_address=self.ip)

    def test_egress_insert(self):
        egress_traffic = PMAcctTrafficEgressFactory.create(ip_src=self.ip)
        self.assertEqual(PmacctTrafficEgress.q.count(), 0)
        self.assertEqual(TrafficVolume.q.count(), 1)
        volume = TrafficVolume.q.one()
        self.assertEqual(volume.type, 'Egress')
        self.assertEqual(volume.amount, egress_traffic.bytes)
        self.assertEqual(volume.packets, egress_traffic.packets)
        self.assertEqual(volume.user, self.user)

    def test_egress_insert_nonexistent_ip(self):
        PMAcctTrafficEgressFactory.create(ip_src=self.bad_ip)
        self.assertEqual(PmacctTrafficEgress.q.count(), 0)
        self.assertEqual(TrafficVolume.q.count(), 0)

    def test_ingress_insert(self):
        ingress_traffic = PMAcctTrafficIngressFactory.create(ip_dst=self.ip)
        self.assertEqual(PmacctTrafficIngress.q.count(), 0)
        self.assertEqual(TrafficVolume.q.count(), 1)
        volume = TrafficVolume.q.one()
        self.assertEqual(volume.type, 'Ingress')
        self.assertEqual(volume.amount, ingress_traffic.bytes)
        self.assertEqual(volume.packets, ingress_traffic.packets)
        self.assertEqual(volume.user, self.user)

    def test_ingress_insert_nonexistent_ip(self):
        PMAcctTrafficIngressFactory.create(ip_dst=self.bad_ip)
        self.assertEqual(PmacctTrafficEgress.q.count(), 0)
        self.assertEqual(TrafficVolume.q.count(), 0)
