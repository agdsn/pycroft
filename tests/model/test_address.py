# Copyright (c) 2019 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from tests import FactoryDataTestBase
from tests.factories.address import AddressFactory
from tests.factories.base import copy_factory


def iter_transaction_parents(t):
    current = t
    while True:
        yield current
        try:
            current = current.parent
        except AttributeError:
            return


def str_id(obj):
    if obj is None:
        return "None"
    return f"0x{(id(obj)):x}"


def print_nesting(session):
    print("→".join(str_id(s) for s in iter_transaction_parents(session.transaction)))


class AddressConstraintsTestCase(FactoryDataTestBase):
    def create_factories(self):
        self.addr_everything = AddressFactory.create()
        self.addr_no_state = AddressFactory.create(state=None)
        self.addr_no_addition = AddressFactory.create(addition=None)
        self.addr_no_addition_and_state = AddressFactory.create(addition=None, state=None)

    def assert_address_cannot_be_added(self, address):
        fail_msg = "Did not get a unique constraint violation when adding a duplicate address"
        new_addr = copy_factory(AddressFactory, address)

        with self.assertUniqueViolation(fail_msg):
            with self.session.begin_nested():
                self.session.add(new_addr)

    def test_address_unique(self):
        for address in [self.addr_everything, self.addr_no_state, self.addr_no_addition,
                        self.addr_no_addition_and_state]:
            with self.subTest(address=address):
                # breakpoint()
                self.assert_address_cannot_be_added(address)
