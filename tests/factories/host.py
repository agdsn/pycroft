import factory
from faker.providers import BaseProvider
from ipaddr import IPv4Network, IPv4Address

from pycroft.model.host import Host, Switch, Interface, IP, SwitchPort
from tests.factories.base import BaseFactory
from tests.factories.facilities import RoomFactory
from tests.factories.net import SubnetFactory, VLANFactory
from tests.factories.user import UserFactory


class UnicastMacProvider(BaseProvider):
    def unicast_mac_address(self):
        mac = [self.generator.random.randint(0x00, 0xff) for i in range(0, 6)]
        mac[0] = mac[0] & 0xfe
        return ':'.join('%02x' % x for x in mac)


factory.Faker.add_provider(UnicastMacProvider)


class IPFactory(BaseFactory):
    class Meta:
        model = IP
        exclude = ('str_address',)

    str_address = factory.Faker('ipv4', network=False)
    address = factory.LazyAttribute(lambda o: IPv4Address(o.str_address))
    # interface = factory.SubFactory(InterfaceFactory)
    subnet = factory.SubFactory(SubnetFactory, address=IPv4Network('0.0.0.0/0'))


class InterfaceFactory(BaseFactory):
    class Meta:
        model = Interface
    mac = factory.Faker('unicast_mac_address')
    # host = factory.SubFactory('HostFactory')
    ip = factory.RelatedFactory(IPFactory, 'interface')


class HostFactory(BaseFactory):
    class Meta:
        model = Host

    owner = factory.SubFactory(UserFactory)
    room = factory.SubFactory(RoomFactory)
    interface = factory.RelatedFactory(InterfaceFactory, 'host')


class SwitchFactory(BaseFactory):
    class Meta:
        model = Switch

    host = factory.SubFactory(HostFactory)
    name = factory.Sequence(lambda n: "Switch {}".format(n))
    management_ip = factory.Faker('ipv4')
    switch_port = factory.RelatedFactory('tests.factories.host.SwitchPortFactory', 'switch')


class SwitchPortFactory(BaseFactory):
    class Meta:
        model = SwitchPort
    switch = factory.SubFactory(SwitchFactory)
    name = factory.Sequence(lambda n: "SwitchPort {}".format(n))

    @factory.post_generation
    def vlans(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of groups were passed in, use them
            for vlan in extracted:
                self.vlans.append(vlan)
        else:
            # Create a default vlan
            self.vlans.append(VLANFactory())
