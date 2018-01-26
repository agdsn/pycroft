import factory
from ipaddr import IPv4Network

from pycroft.model.net import VLAN, Subnet
from tests.factories.base import BaseFactory


class VLANFactory(BaseFactory):
    class Meta:
        model = VLAN

    name = factory.Sequence(lambda n: "vlan{}".format(n+1))
    vid = factory.Sequence(lambda n: n+1)


class SubnetFactory(BaseFactory):
    class Meta:
        model = Subnet
        exclude = ('str_address',)

    str_address = factory.Faker('ipv4', network=True)
    address = factory.LazyAttribute(lambda o: IPv4Network(o.str_address))
    vlan = factory.SubFactory(VLANFactory)
