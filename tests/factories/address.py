from factory import Faker

from pycroft.model.address import Address
from tests.factories.base import BaseFactory


class AddressFactory(BaseFactory):
    class Meta:
        model = Address

    street = Faker("street_name")
    number = Faker("random_digit")
    addition = Faker("secondary_address")
    zip_code = Faker("zipcode")
    city = "Dresden"
    state = "Sachsen"
    country = "Germany"
