import pytest
from sqlalchemy import inspect, func
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from pycroft.lib import address
from pycroft.model.address import Address
from tests.factories.address import AddressFactory


class TestAddress:
    @pytest.fixture(scope="class")
    def known_address(self, class_session: Session) -> Address:
        return AddressFactory.create()

    @staticmethod
    def count_addrs(session: Session) -> int:
        return session.scalar(select(func.count(Address.id)))

    def test_new_address_gets_created(self, session: Session):
        old_count = self.count_addrs(session)
        new_addr = address.get_or_create_address(
            street='Wundtstraße',
            number='3',
            addition=None,
            zip_code='01217',
            city='Dresden',
        )
        session.flush()
        assert inspect(new_addr).has_identity, "Created address has no db identity"
        assert self.count_addrs(session) == old_count + 1

    def test_existing_address_gets_returned(self, known_address: Address, session: Session):
        old_count = self.count_addrs(session)
        new_addr = address.get_or_create_address(
            **{key: val for key, val in known_address.__dict__.items()
               if key in {'street', 'number', 'addition', 'zip_code', 'city', 'state', 'country'}}
        )
        session.flush()
        assert inspect(new_addr).has_identity, "Created address has no db identity"
        assert self.count_addrs(session) == old_count

    def test_new_address_gets_server_defaults(self, session: Session):
        """Test that missing entries get the server default and not the empty string."""
        new_addr = address.get_or_create_address(
            street='Wundtstraße',
            number='3',
            addition=None,
            zip_code='01217',
            city=None,
            state=None,
            country=None,
        )
        session.flush()
        session.refresh(new_addr)
        assert new_addr.city == 'Dresden', "City not set"
        # state's default actually _is_ ''
        assert new_addr.country == 'Germany', "Country not set"
