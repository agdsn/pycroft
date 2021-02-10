from sqlalchemy import inspect

from pycroft.lib import address
from pycroft.model.address import Address
from tests import FactoryDataTestBase
from tests.factories.address import AddressFactory


class AddressTest(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.known_address = AddressFactory()

    def count_addrs(self):
        return self.session.query(Address).count()

    def test_new_address_gets_created(self):
        old_count = self.count_addrs()
        new_addr = address.get_or_create_address(
            street='Wundtstraße',
            number='3',
            zip_code='01217',
            city='Dresden',
        )
        self.session.commit()

        assert inspect(new_addr).has_identity, "Created address has no db identity"

        assert self.count_addrs() == old_count + 1

    def test_existing_address_gets_returned(self):
        old_count = self.count_addrs()
        new_addr = address.get_or_create_address(
            **{key: val for key, val in self.known_address.__dict__.items()
               if key in {'street', 'number', 'addition', 'zip_code', 'city', 'state', 'country'}}
        )
        self.session.commit()

        assert inspect(new_addr).has_identity, "Created address has no db identity"

        assert self.count_addrs() == old_count

    def test_new_address_gets_server_defaults(self):
        """Test that missing entries get the server default and not the empty string."""
        new_addr = address.get_or_create_address(
            street='Wundtstraße',
            number='3',
            zip_code='01217',
            city=None,
            state=None,
            country=None,
        )
        self.session.commit()
        self.session.refresh(new_addr)

        assert new_addr.city == 'Dresden', "City not set"
        # state's default actually _is_ ''
        assert new_addr.country == 'Germany', "Country not set"
