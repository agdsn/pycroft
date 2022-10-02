# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from factory import SubFactory, LazyAttribute, Sequence, Trait, RelatedFactoryList, post_generation
from factory.faker import Faker

from pycroft.model.facilities import Site, Building, Room
from pycroft.model.port import PatchPort
from .finance import AccountFactory
from .base import BaseFactory
from .address import AddressFactory


class SiteFactory(BaseFactory):
    class Meta:
        model = Site

    name = Faker('street_name')


class BuildingFactory(BaseFactory):
    class Meta:
        model = Building

    site = SubFactory(SiteFactory)

    number = Sequence(lambda n: str(n))
    street = LazyAttribute(lambda b: b.site.name)
    short_name = LazyAttribute(lambda b: f"{b.street[:3]}{b.number}")
    fee_account = SubFactory(AccountFactory, type='REVENUE')


class RoomFactory(BaseFactory):
    class Meta:
        model = Room

    number = Faker('numerify', text='## #')
    level = Faker('random_int', min=0, max=16)
    # This fix value makes more sense than a random one in most cases
    inhabitable = True

    building = SubFactory(BuildingFactory)
    address = SubFactory(AddressFactory)
    patch_ports = []

    class Params:
        # Adds a patched PatchPort with a subnet
        patched_with_subnet = Trait(
            patch_ports=RelatedFactoryList('tests.factories.facilities.PatchPortFactory', 'room',
                                           size=1,
                                           patched=True,
                                           switch_port__default_vlans__create_subnet=True)
        )


class PatchPortFactory(BaseFactory):
    class Meta:
        model = PatchPort

    room = SubFactory(RoomFactory)
    switch_room = None
    name = "??"
    switch_port = None

    class Params:
        patched = Trait(
            switch_port=SubFactory('tests.factories.host.SwitchPortFactory')
        )

    # noinspection PyMethodParameters
    @post_generation
    def post(obj: PatchPort, create, extracted, **kwargs):
        # Ensure that patched ports terminate in the switch room
        if obj.switch_port:
            obj.switch_room = obj.switch_port.switch.host.room
        else:
            obj.switch_room = RoomFactory.build()

