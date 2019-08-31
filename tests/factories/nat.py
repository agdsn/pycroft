from factory import Sequence, SubFactory, Faker

from pycroft.model.nat import NATDomain, OutsideIPAddress
from pycroft.model.nat import InsideNetwork, Translation, Forwarding, \
    DHCPHostReservation
from .base import BaseFactory


class NatDomainFactory(BaseFactory):
    class Meta:
        model = NATDomain

    name = Sequence(lambda n: f"NAT Domain {n + 1}")


class OutsideIpAddressFactory(BaseFactory):
    class Meta:
        model = OutsideIPAddress

    nat_domain = SubFactory(NatDomainFactory)
    ip_address = Faker('ipv4', network=False)
    owner = None


class InsideNetworkFactory(BaseFactory):
    # TODO this should be filled with all available inside networks
    class Meta:
        model = InsideNetwork

    nat_domain = SubFactory(NatDomainFactory)
    ip_network = Faker('ipv4', network=True)
    gateway = Faker('ipv4', network=False)


class TranslationFactory(BaseFactory):
    class Meta:
        model = Translation

    pass


class ForwardingFactory(BaseFactory):
    class Meta:
        model = Forwarding

    pass


class DhcpHostReservationFactory(BaseFactory):
    class Meta:
        model = DHCPHostReservation

    pass


