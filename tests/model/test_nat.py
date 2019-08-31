from typing import List

from pycroft.model.nat import NATDomain
from tests import FactoryDataTestBase
from tests.factories import ConfigFactory, UserFactory
from tests.factories.nat import NatDomainFactory, OutsideIpAddressFactory


class NatTestBase(FactoryDataTestBase):
    def create_factories(self):
        ConfigFactory.create()
        self.nat_domain = NatDomainFactory()


class TrivialNatModelTestCase(NatTestBase):
    def create_factories(self):
        super().create_factories()

    def test_one_natdomain(self):
        doms: List[NATDomain] = NATDomain.q.all()
        self.assertEqual(len(doms), 1)
        dom = doms[0]
        self.assertEqual(dom.name, self.nat_domain.name)


class SimpleNatModelTestCase(NatTestBase):
    def create_factories(self):
        super().create_factories()
        self.user = UserFactory.create()
        self.outside_ip = OutsideIpAddressFactory(owner=self.user,
                                                  nat_domain=self.nat_domain)
        # TODO later check that this doesn't work because every outside_ip needs a translation
        # TODO add a pool of inside networks

    def test_forwardings_correct(self):
        domain: NATDomain = NATDomain.q.one()
        self.assertEqual(domain.name, self.nat_domain.name)
