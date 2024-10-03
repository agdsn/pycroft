#  Copyright (c) 2024. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import factory
from tests.factories.base import BaseFactory
from pycroft.model.mpsk_client import MPSKClient

from tests.factories.user import UserFactory
from tests.factories.host import UnicastMacProvider

factory.Faker.add_provider(UnicastMacProvider)


class BareMPSKFactory(BaseFactory):
    """A host without owner or interface."""

    class Meta:
        model = MPSKClient

    mac = factory.Faker("unicast_mac_address")
    name = factory.Faker("name")


class MPSKFactory(BareMPSKFactory):

    owner = factory.SubFactory(UserFactory)
