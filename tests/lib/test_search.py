#  Copyright (c) 2021. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import datetime

from pycroft.helpers.interval import single
from pycroft.lib.search import user_search_query
from tests.legacy_base import FactoryDataTestBase
from tests.factories import UserWithHostFactory, PropertyGroupFactory, \
    MembershipFactory


def s(**kw):
    return user_search_query(**kw).all()


class UserBase(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        # this user exists so that a malfunction a la „every user is returned“
        # is distinguishable from the case „the (one) correct user is returned“.
        UserWithHostFactory.create(name='Franz', login='franz', email='fr@a.nz')


class SearchUserBaseDataTest(UserBase):
    def create_factories(self):
        super().create_factories()
        self.property_group = PropertyGroupFactory.create()
        self.user = UserWithHostFactory.create(
            name='Hans Müller',
            login='hans.mueller',
            email='hans@mueller.com',
        )

    def test_name_search(self):
        assert s(name='Hans') == [self.user]
        assert s(name='Corect, Horse') == []

    def test_login_search(self):
        assert s(login='mueller') == [self.user]
        assert s(login='correcthorsebatterystaple') == []

    def test_email_search(self):
        assert s(email='mueller.com') == [self.user]
        assert s(email='franz.com') == []

    def test_user_id_search(self):
        assert s(user_id=self.user.id) == [self.user]
        assert s(user_id=1e9) == []

    # one might add tests for person_id, building, mac, query …


class UserTest(UserBase):
    def create_factories(self):
        super().create_factories()
        self.group, self.old_group = PropertyGroupFactory.create_batch(2)
        self.user = UserWithHostFactory.create(
            host__interface__mac='00:de:ad:be:ef:00',
            with_membership=True,
            membership__group=self.group,
        )
        self.old_property_group = PropertyGroupFactory.create()
        MembershipFactory.create(
            user=self.user, group=self.old_group,
            active_during=single(datetime.datetime(2020, 1, 1)),
        )

    def test_past_property_group_search(self):
        assert s(property_group_id=self.old_group.id) == []

    def test_property_group_search(self):
        assert s(property_group_id=self.group.id) == [self.user]
