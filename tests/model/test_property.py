# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime, timedelta

from pycroft.model import session, user
from pycroft.model.property import current_property
from pycroft.model.user import Group, Membership, PropertyGroup
from tests import FactoryDataTestBase, factories
from tests.factories.property import MembershipFactory, PropertyGroupFactory


class PropertyDataTestBase(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.user = factories.UserFactory()
        self.prop1 = 'test1'
        self.prop2 = 'test2'
        self.property_group1 = factories.PropertyGroupFactory(granted={self.prop1})
        self.property_group2 = factories.PropertyGroupFactory(granted={self.prop1, self.prop2})


class Test_PropertyResolving(PropertyDataTestBase):
    def test_assert_correct_fixture(self):
        """simply test that fixtures work
        """
        assert Membership.q.count() == 0

        assert not self.user.has_property(self.prop1)
        assert not self.user.has_property(self.prop2)

        assert len(self.property_group1.properties) == 1
        assert len(self.property_group2.properties) == 2
        assert self.prop1 in self.property_group1.properties
        assert self.prop1 in self.property_group2.properties
        assert self.prop2 in self.property_group2.properties

    def test_add_membership(self):
        # add membership to group1
        membership = Membership(
            begins_at=session.utcnow(),
            user=self.user,
            group=self.property_group1
        )
        session.session.add(membership)
        session.session.commit()

        assert self.user.has_property(self.prop1)
        assert not self.user.has_property(self.prop2)

        # add membership to group2
        membership = Membership(
            begins_at=session.utcnow(),
            user=self.user,
            group=self.property_group2
        )
        session.session.add(membership)
        session.session.commit()

        assert self.user.has_property(self.prop1)
        assert self.user.has_property(self.prop2)

    def test_add_timed_membership(self):
        # add membership to group1
        now = session.utcnow()
        membership = Membership(
            begins_at=now,
            user=self.user,
            group=self.property_group1
        )
        membership.ends_at = membership.begins_at + timedelta(days=3)
        session.session.add(membership)
        session.session.commit()

        assert self.user.has_property(self.prop1)
        assert not self.user.has_property(self.prop2)

        # add expired membership to group2
        membership = Membership(
            begins_at=now - timedelta(hours=2),
            user=self.user,
            group=self.property_group2
        )
        membership.ends_at = now - timedelta(hours=1)
        session.session.add(membership)
        session.session.commit()

        assert self.user.has_property(self.prop1)
        assert not self.user.has_property(self.prop2)

    def test_disable_membership(self):
        # add membership to group1
        membership = Membership(
            begins_at=session.utcnow() - timedelta(hours=2),
            user=self.user,
            group=self.property_group1
        )
        session.session.add(membership)
        session.session.commit()

        assert self.user.has_property(self.prop1)
        membership.disable(session.utcnow() - timedelta(hours=1))
        session.session.commit()
        assert self.property_group1 not in self.user.active_property_groups()
        assert not self.user.has_property(self.prop1)

        # add membership to group1
        membership = Membership(
            begins_at=session.utcnow(),
            user=self.user,
            group=self.property_group1
        )
        session.session.add(membership)
        session.session.commit()

        assert self.user.has_property(self.prop1)

        # add membership to group2
        membership = Membership(
            begins_at=session.utcnow() - timedelta(hours=2),
            user=self.user,
            group=self.property_group2
        )
        session.session.add(membership)
        session.session.commit()

        assert self.user.has_property(self.prop1)
        assert self.user.has_property(self.prop2)

        # disables membership in group2
        membership.disable(session.utcnow() - timedelta(hours=1))
        session.session.commit()
        assert self.user.has_property(self.prop1)
        assert not self.user.has_property(self.prop2)


class Test_MembershipValidators(PropertyDataTestBase):
    def test_start_date_default(self):
        # add membership to group1
        p1 = Membership(user=self.user, group=self.property_group1)
        session.session.add(p1)
        session.session.commit()

        session.session.refresh(p1)
        p = p1
        assert p is not None
        assert p.begins_at is not None
        assert p.ends_at is None

    def test_end_date_before_start(self):
        # add membership to group1
        p1 = Membership(user=self.user, group=self.property_group1)
        p1.begins_at = session.utcnow()

        def set_old_date():
            """ Set ends_at before begins_at
            """
            p1.ends_at = session.utcnow() - timedelta(hours=2)

        self.assertRaisesRegexp(
            AssertionError,
            "begins_at must be before ends_at",
            set_old_date
        )

    def test_start_date_after_end(self):
        # add membership to group1
        now = session.utcnow()
        self.assertRaisesRegexp(
            AssertionError,
            "begins_at must be before ends_at",
            Membership, user=self.user, group=self.property_group1,
            begins_at=now + timedelta(days=1), ends_at=now
        )

    def test_set_correct_dates(self):
        # add membership to group1
        p1 = Membership(user=self.user, group=self.property_group1)
        p1.begins_at = session.utcnow()
        p1.ends_at = session.utcnow()

        session.session.add(p1)
        session.session.commit()

        p1.begins_at = session.utcnow() - timedelta(days=3)
        p1.ends_at = session.utcnow() + timedelta(days=3)

        session.session.commit()

    def test_clear_end_date(self):
        # add membership to group1
        p1 = Membership(user=self.user, group=self.property_group1)
        p1.begins_at = session.utcnow()
        p1.ends_at = session.utcnow()
        session.session.add(p1)
        session.session.commit()

        # test if membership in database
        p1 = Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        assert p1.ends_at is not None

        # clear ends_at
        p1.ends_at = None
        session.session.commit()

        p1 = Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        assert p1.ends_at is None


class Test_View_Only_Shortcut_Properties(PropertyDataTestBase):
    def test_group_users(self):
        assert len(self.property_group1.users) == 0
        assert len(self.property_group1.active_users()) == 0

        # add membership to group1
        p1 = Membership(begins_at=session.utcnow() - timedelta(hours=2),
                        user=self.user, group=self.property_group1)
        session.session.add(p1)
        session.session.commit()

        assert len(self.property_group1.users) == 1
        assert len(self.property_group1.active_users()) == 1

        p1.disable(session.utcnow() - timedelta(hours=1))
        session.session.commit()
        assert len(self.property_group1.users) == 1
        assert len(self.property_group1.active_users()) == 0

    def test_user_property_groups(self):
        # first have no property group
        assert len(self.user.property_groups) == 0
        assert len(self.user.active_property_groups()) == 0

        # add one active property group
        p1 = Membership(begins_at=session.utcnow() - timedelta(hours=2),
                        user=self.user, group=self.property_group1)
        session.session.add(p1)
        session.session.commit()
        f = Membership.q.first()
        assert f.active()
        assert len(self.user.property_groups) == 1
        assert len(self.user.active_property_groups()) == 1

        # add a second active property group - count should be 2
        p1 = Membership(begins_at=session.utcnow() - timedelta(hours=2),
                        user=self.user, group=self.property_group2)
        session.session.add(p1)
        session.session.commit()
        assert len(self.user.property_groups) == 2
        assert len(self.user.active_property_groups()) == 2

        # disable the second group. active should be one, all 2
        p1.disable(session.utcnow() - timedelta(hours=1))
        session.session.commit()
        assert len(self.user.property_groups) == 2
        assert len(self.user.active_property_groups()) == 1

        # test a join
        res = session.session.query(
            user.User, PropertyGroup.id
        ).join(user.User.property_groups).filter(
            user.User.id == self.user.id
        ).distinct().count()
        assert res == 2

        # reenable it - but with a deadline - both counts should be 2
        p1.ends_at = session.utcnow() + timedelta(days=1)
        session.session.commit()
        assert len(self.user.property_groups) == 2
        assert len(self.user.active_property_groups()) == 2

        # Add a second membership to the first group
        # should not affect the count
        p1 = Membership(begins_at=session.utcnow() - timedelta(hours=2),
                        user=self.user, group=self.property_group1)
        session.session.add(p1)
        session.session.commit()
        assert len(self.user.property_groups) == 2
        assert len(self.user.active_property_groups()) == 2

        # disabling the new one should also not affect.
        p1.disable(session.utcnow() - timedelta(hours=1))
        session.session.commit()
        assert len(self.user.property_groups) == 2
        assert len(self.user.active_property_groups()) == 2

        # test a join
        res = session.session.query(
            user.User, PropertyGroup
        ).join(user.User.property_groups).filter(
            user.User.id == self.user.id
        ).distinct().count()
        assert res == 2


class Test_Membership(PropertyDataTestBase):
    def test_active_instance_property(self):
        p1 = Membership(begins_at=session.utcnow() - timedelta(hours=2),
                        user=self.user, group=self.property_group1)
        assert p1.active()
        session.session.add(p1)
        session.session.commit()

        p1 = Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        assert p1.active()

        p1.disable(session.utcnow() - timedelta(hours=1))
        session.session.commit()

        p1 = Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        assert not p1.active()

        p1.ends_at = None
        session.session.commit()

        p1 = Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        assert p1.active()

        session.session.delete(p1)
        session.session.commit()

        p1 = Membership(begins_at=session.utcnow() - timedelta(hours=2),
                        user=self.user, group=self.property_group1)
        session.session.add(p1)
        session.session.commit()

        p1 = Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        assert p1.active()

        p1.begins_at = session.utcnow() + timedelta(days=2)
        session.session.commit()

        p1 = Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        assert not p1.active()

        p1.disable(session.utcnow() - timedelta(hours=1))
        session.session.commit()

        p1 = Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        assert not p1.active()

        p1.ends_at = p1.begins_at + timedelta(days=1)
        session.session.commit()

        p1 = Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        assert not p1.active()

        p1.begins_at = session.utcnow() - timedelta(days=1)
        session.session.commit()

        p1 = Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        assert p1.active()


class TestGroup(PropertyDataTestBase):
    def add_membership(self):
        session.session.add(Membership(user=self.user,
                                                group=self.property_group1))
        session.session.commit()

    def test_active_users(self):
        assert self.property_group1.active_users() == []
        self.add_membership()
        assert self.property_group1.active_users() == [self.user]

    def create_active_users_query(self):
        active_users = Group.active_users().where(
            Group.id == self.property_group1.id)
        return session.session.query(user.User).from_statement(active_users)

    def test_active_users_expression(self):
        query = self.create_active_users_query()
        assert query.all() == []
        self.add_membership()
        query = self.create_active_users_query()
        assert query.all() == [self.user]


class CurrentPropertyViewTest(FactoryDataTestBase):
    def setUp(self):
        super().setUp()
        property_group_data = {
            # name, granted, denied
            'active': ({'login', 'mail'}, set()),
            'mail_only': ({'mail'}, set()),
            'violation': (set(), {'login'}),
        }
        self.groups = {}
        for name, (granted, denied) in property_group_data.items():
            self.groups[name] = PropertyGroupFactory.create(name=name,
                                                            granted=granted,
                                                            denied=denied)

        self.users = dict(zip(['active', 'mail', 'violator', 'former'],
                              factories.UserFactory.create_batch(4)))

        memberships = [
            # user, group, delta_days_start, delta_days_end
            ('active', 'active', -1, None),
            ('mail', 'mail_only', -1, +1),
            ('mail', 'active', +2, None),
            ('violator', 'active', -1, None),
            ('violator', 'violation', -1, None),
            ('former', 'active', -10, -1),
            ('former', 'violation', -9, -5),
        ]
        for username, groupname, delta_days_start, delta_days_end in memberships:
            start = (datetime.now() + timedelta(delta_days_start)
                     if delta_days_start is not None else None)
            end = (datetime.now() + timedelta(delta_days_end)
                   if delta_days_end is not None else None)

            MembershipFactory.create(user=self.users[username],
                                     group=self.groups[groupname],
                                     begins_at=start, ends_at=end)
        session.session.commit()

    def test_current_properties_of_user(self):
        rows = (session.session.query(current_property.table.c.property_name)
                .add_columns(user.User.login.label('login'))
                .join(user.User.current_properties)
                .all())
        login = self.users['active'].login
        expected_results = [
            # name, granted, denied
            ('active', ['mail', 'login'], []),
            ('mail', ['mail'], ['login']),
            ('former', [], ['mail', 'login']),
            ('violator', ['mail'], ['login'])
        ]
        for user_key, granted, denied in expected_results:
            login = self.users[user_key].login
            with self.subTest(login=login):
                for granted_prop in granted:
                    assert (granted_prop, login) in rows
                for denied_prop in denied:
                    assert (denied_prop, login) not in rows

    def test_current_granted_or_denied_properties_of_user(self):
        rows = (session.session.query(current_property.table.c.property_name)
                .add_columns(user.User.login.label('login'))
                .join(user.User.current_properties_maybe_denied)
                .all())
        # This checks that the violator's 'login' property is in the view as well
        # when ignoring the `denied` column
        assert ('login', self.users['violator'].login) in rows
