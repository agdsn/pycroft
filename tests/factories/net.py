import factory
from ipaddr import IPv4Network

from pycroft.model.net import VLAN, Subnet
from tests.factories.base import BaseFactory


class VLANFactory(BaseFactory):
    class Meta:
        model = VLAN

    name = factory.Sequence(lambda n: "vlan{}".format(n+1))
    vid = factory.Sequence(lambda n: n+1)


def _random_subnet():
    ipv4_factory = factory.Faker('ipv4', network=True)
    while True:
        str_network = ipv4_factory.generate(extra_kwargs={})
        network = IPv4Network(str_network)
        if network.numhosts >= 4:
            return network

class SubnetFactory(BaseFactory):
    class Meta:
        model = Subnet

    address = factory.LazyAttribute(lambda o: _random_subnet())
    vlan = factory.SubFactory(VLANFactory)
