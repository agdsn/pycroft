import factory
from netaddr import IPNetwork

from pycroft.model.net import VLAN, Subnet
from tests.factories.base import BaseFactory


class VLANFactory(BaseFactory):
    class Meta:
        model = VLAN

    name = factory.Sequence(lambda n: f"vlan{n+1}")
    vid = factory.Sequence(lambda n: n+1)

    class Params:
        create_subnet = factory.Trait(
            subnets=factory.RelatedFactoryList('tests.factories.net.SubnetFactory', 'vlan', size=1)
        )


class SubnetFactory(BaseFactory):
    class Meta:
        model = Subnet

    address = factory.Sequence(lambda n: IPNetwork(f"141.{n // 255}.{n % 255}.0/29"))
    vlan = factory.SubFactory(VLANFactory)
    reserved_addresses_top = 0
    reserved_addresses_bottom = 0
