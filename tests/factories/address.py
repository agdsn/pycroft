from factory import Faker, LazyAttribute

from pycroft.model.address import Address
from tests.factories.base import BaseFactory


class AddressFactory(BaseFactory):
    class Meta:
        model = Address
        exclude = ('_number',)

    street = Faker("street_name")
    _number = Faker("random_digit")
    number = LazyAttribute(lambda o: str(o._number))
    addition = Faker("secondary_address")
    zip_code = Faker("zipcode")
    city = "Dresden"
    state = "Sachsen"
    country = "Germany"
