# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func
from sqlalchemy.future import select

from pycroft.helpers.interval import closedopen, starting_from
from pycroft.model.property import current_property, evaluate_properties
from pycroft.model.user import Group, Membership, PropertyGroup, User
from tests import factories
from tests.factories.property import MembershipFactory, PropertyGroupFactory


@pytest.fixture(scope='module')
def user(module_session):
    return factories.UserFactory()

PROP1 = 'test1'
PROP2 = 'test2'

@pytest.fixture(scope='module')
def property_group1(module_session):
    with module_session.begin_nested():
        return factories.PropertyGroupFactory(granted={PROP1})

@pytest.fixture(scope='module')
def property_group2(module_session):
    with module_session.begin_nested():
        return factories.PropertyGroupFactory(granted={PROP1, PROP2})


def test_fixtures_correct(session, user, property_group1, property_group2):
    """simply test that fixtures work
    """
    assert session.scalar(func.count(Membership.id)) == 0

    assert not user.has_property(PROP1)
    assert not user.has_property(PROP2)

    assert len(property_group1.properties) == 1
    assert len(property_group2.properties) == 2
    assert PROP1 in property_group1.properties
    assert PROP1 in property_group2.properties
    assert PROP2 in property_group2.properties


class Test_PropertyResolving:
    def test_add_membership(self, session, utcnow, user, property_group1, property_group2):
        # add membership to group1
        with session.begin_nested():
            session.add(
                Membership(
                    active_during=starting_from(utcnow),
                    user=user,
                    group=property_group1,
                )
            )
        session.refresh(user)
        assert user.has_property(PROP1)
        assert not user.has_property(PROP2)

        # add membership to group2
        with session.begin_nested():
            session.add(
                Membership(
                    active_during=starting_from(utcnow),
                    user=user,
                    group=property_group2,
                )
            )
        session.refresh(user)
        assert user.has_property(PROP1)
        assert user.has_property(PROP2)

    def test_add_timed_membership(self, session, utcnow, user, property_group1, property_group2):
        with session.begin_nested():
            session.add(Membership(
                active_during=closedopen(utcnow, utcnow + timedelta(days=3)),
                user=user,
                group=property_group1
            ))
        session.refresh(user)
        assert user.has_property(PROP1)
        assert not user.has_property(PROP2)

        with session.begin_nested():
            # add expired membership to group2
            session.add(Membership(
                active_during=closedopen(utcnow - timedelta(hours=2), utcnow - timedelta(hours=1)),
                user=user,
                group=property_group2
            ))
        session.refresh(user)
        assert user.has_property(PROP1)
        assert not user.has_property(PROP2)

    def test_disable_membership(self, session, utcnow, user, property_group1, property_group2):
        # add membership to group1
        membership = Membership(
            active_during=starting_from(utcnow - timedelta(hours=2)),
            user=user,
            group=property_group1
        )
        with session.begin_nested():
            session.add(membership)
        session.refresh(user)
        assert user.has_property(PROP1)

        with session.begin_nested():
            membership.disable(utcnow - timedelta(hours=1))
        session.refresh(user)
        assert property_group1 not in user.active_property_groups()
        assert not user.has_property(PROP1)

        with session.begin_nested():
            # add membership to group1
            session.add(
                Membership(
                    active_during=starting_from(utcnow),
                    user=user,
                    group=property_group1,
                )
            )
        session.refresh(user)
        assert user.has_property(PROP1)

        # add membership to group2
        membership = Membership(
            active_during=starting_from(utcnow - timedelta(hours=2)),
            user=user,
            group=property_group2
        )
        with session.begin_nested():
            session.add(membership)
        session.refresh(user)
        assert user.has_property(PROP1)
        assert user.has_property(PROP2)

        # disables membership in group2
        with session.begin_nested():
            membership.disable(utcnow - timedelta(hours=1))
        session.refresh(user)
        assert user.has_property(PROP1)
        assert not user.has_property(PROP2)


class Test_View_Only_Shortcut_Properties:
    def test_group_users(self, session, utcnow, user, property_group1, property_group2):
        assert len(property_group1.users) == 0
        assert len(property_group1.active_users()) == 0

        # add membership to group1
        p1 = Membership(
            active_during=starting_from(utcnow - timedelta(hours=2)),
            user=user,
            group=property_group1,
        )
        with session.begin_nested():
            session.add(p1)
        session.refresh(property_group1)
        assert len(property_group1.users) == 1
        assert len(property_group1.active_users()) == 1

        with session.begin_nested():
            p1.disable(utcnow - timedelta(hours=1))
        session.refresh(property_group1)
        assert len(property_group1.users) == 1
        assert len(property_group1.active_users()) == 0

    def test_user_property_groups(self, session, utcnow, user, property_group1, property_group2):
        # first have no property group
        assert len(user.property_groups) == 0
        assert len(user.active_property_groups()) == 0

        # add one active property group
        p1 = Membership(
            active_during=starting_from(utcnow - timedelta(hours=2)),
            user=user,
            group=property_group1,
        )
        with session.begin_nested():
            session.add(p1)
        session.refresh(user)
        f = Membership.q.first()
        assert utcnow in f.active_during
        assert len(user.property_groups) == 1
        assert len(user.active_property_groups()) == 1

        # add a second active property group - count should be 2
        p1 = Membership(
            active_during=starting_from(utcnow - timedelta(hours=2)),
            user=user,
            group=property_group2,
        )
        with session.begin_nested():
            session.add(p1)
        session.refresh(user)
        assert len(user.property_groups) == 2
        assert len(user.active_property_groups()) == 2

        # disable the second group. active should be one, all 2
        with session.begin_nested():
            p1.disable(utcnow - timedelta(hours=1))
        session.refresh(user)
        assert len(user.property_groups) == 2
        assert len(user.active_property_groups()) == 1

        # test a join
        res = session.query(
            User, PropertyGroup.id
        ).join(User.property_groups).filter(
            User.id == user.id
        ).distinct().count()
        assert res == 2

        # reenable it - but with a deadline - both counts should be 2
        with session.begin_nested():
            p1.active_during = closedopen(p1.active_during.begin,
                                          utcnow + timedelta(days=1))
        session.refresh(user)
        assert len(user.property_groups) == 2
        assert len(user.active_property_groups()) == 2

        # test a join
        res = session.query(
            User, PropertyGroup
        ).join(User.property_groups).filter(
            User.id == user.id
        ).distinct().count()
        assert res == 2


def h(x):
    return timedelta(hours=x)


def d(x):
    return timedelta(days=x)


class Test_Membership:
    @pytest.mark.parametrize('rel_begin, rel_end, active_expected', [
        (- h(2), None, True),
        (+ h(2), None, False),
        (- h(2), None, True),
        (+ d(2), None, False),
        (+ d(2), + d(3), False),
        (- d(1), + d(3), True),
    ])
    def test_active_instance_property(
        self,
        rel_begin, rel_end, active_expected,
        session, utcnow, user, property_group1
    ):
        interval = closedopen(utcnow + rel_begin, rel_end and utcnow + rel_end)
        mem = Membership(active_during=interval, user=user, group=property_group1)
        with session.begin_nested():
            session.add(mem)
        session.refresh(mem)
        assert (utcnow in mem.active_during) == active_expected

    def test_active_disable(self, session, utcnow, user, property_group1):
        mem = Membership(
            active_during=starting_from(utcnow - timedelta(hours=2)),
            user=user,
            group=property_group1,
        )
        with session.begin_nested():
            session.add(mem)
        assert utcnow in mem.active_during

        # disable: [NOW - 2h,) → [NOW - 2h, NOW - 1h)
        with session.begin_nested():
            mem.disable(utcnow - timedelta(hours=1))
        session.refresh(mem)
        assert utcnow not in mem.active_during


class TestGroup:
    @pytest.fixture(scope='class')
    def membership(self, class_session, user, utcnow, property_group1):
        return Membership(
            user=user,
            group=property_group1,
            active_during=starting_from(utcnow),
        )

    @pytest.fixture
    def add_membership(self, membership, session):
        def _add_membership():
            with session.begin_nested():
                session.add(membership)
        return _add_membership

    def test_active_users(self, session, user, add_membership, property_group1):
        assert property_group1.active_users() == []
        add_membership()
        session.refresh(property_group1)
        assert property_group1.active_users() == [user]

    @pytest.fixture
    def create_active_users_query(self, session, property_group1):
        def _create_active_users_query():
            active_users = Group.active_users().where(
                Group.id == property_group1.id)
            return session.query(User).from_statement(active_users)
        return _create_active_users_query

    def test_active_users_expression(self, session, user, property_group1,
                                     create_active_users_query, add_membership):
        query = create_active_users_query()
        assert query.all() == []
        add_membership()
        query = create_active_users_query()
        assert query.all() == [user]


class TestCurrentPropertyView:
    @pytest.fixture(scope='class')
    def groups(self, class_session):
        property_group_data = {
            # name, granted, denied
            'active': ({'login', 'mail'}, set()),
            'mail_only': ({'mail'}, set()),
            'violation': (set(), {'login'}),
        }
        return {
            name: PropertyGroupFactory.create(
                name=name, granted=granted, denied=denied
            )
            for name, (granted, denied) in property_group_data.items()
        }

    @pytest.fixture(scope='class')
    def users(self, class_session):
        return {
            key: factories.UserFactory.create(login=f'user-{key}')
            for key in 'active mail violator former'.split()
        }

    @pytest.fixture(scope='class', autouse=True)
    def memberships(self, class_session, users, groups):
        mem_data = [
            # user, group, delta_days_start, delta_days_end
            ('active', 'active', -1, None),
            ('mail', 'mail_only', -1, +1),
            ('mail', 'active', +2, None),
            ('violator', 'active', -1, None),
            ('violator', 'violation', -1, None),
            ('former', 'active', -10, -1),
            ('former', 'violation', -9, -5),
        ]
        memberships = [MembershipFactory.create(
            user=users[username],
            group=groups[groupname],
            active_during=(closedopen(
                (datetime.now() + timedelta(delta_days_start)
                 if delta_days_start is not None else None),
                (datetime.now() + timedelta(delta_days_end)
                 if delta_days_end is not None else None),
            )))
            for username, groupname, delta_days_start, delta_days_end in mem_data
        ]
        return memberships

    def test_current_properties_of_user(self, session, users):
        rows = (session.query(current_property.table.c.property_name)
                .add_columns(User.login.label('login'))
                .join(User.current_properties)
                .all())
        login = users['active'].login
        expected_results = [
            # name, granted, denied
            ('active', ['mail', 'login'], []),
            ('mail', ['mail'], ['login']),
            ('former', [], ['mail', 'login']),
            ('violator', ['mail'], ['login'])
        ]
        for user_key, granted, denied in expected_results:
            login = users[user_key].login
            for granted_prop in granted:
                assert (granted_prop, login) in rows
            for denied_prop in denied:
                assert (denied_prop, login) not in rows

    def test_current_granted_or_denied_properties_of_user(self, session, users):
        rows = (session.query(current_property.table.c.property_name)
                .add_columns(User.login.label('login'))
                .join(User.current_properties_maybe_denied)
                .all())
        # This checks that the violator's 'login' property is in the view as well
        # when ignoring the `denied` column
        assert ('login', users['violator'].login) in rows


def _iso(date):
    return datetime.fromisoformat(f'{date}T00:00:00+00:00')


class TestEvaluateProperties:
    @pytest.fixture(scope='class')
    def groups(self, class_session):
        return [
            PropertyGroupFactory(granted={'good', 'other'}),
            PropertyGroupFactory(granted={'bad'}, denied={'good'}),
        ]

    @pytest.fixture(scope='class')
    def mem1(self, class_session, user, groups):
        # mem1: [2000-01-01 ---------------------- 2000-01-03)
        return MembershipFactory.create(
            user=user,
            active_during=closedopen(_iso('2000-01-01'), _iso('2000-01-03')),
            group=groups[0],
        )

    @pytest.fixture(scope='class')
    def mem2(self, class_session, user, groups):
        # mem2:                  [2000-01-02 ---------------------- 2000-01-04)
        return MembershipFactory.create(
            user=user,
            active_during=closedopen(_iso('2000-01-02'), _iso('2000-01-04')),
            group=groups[1],
        )

    @pytest.fixture
    def props_at(self, session, user):
        def _props_at(when) -> set:
            props = evaluate_properties(when=when, name='props')
            stmt = (
                select(props.c.property_name, props.c.denied)
                    .select_from(props)
                    .join(User, onclause=User.id == props.c.user_id)
                    .where(User.id == user.id)
            )
            rows = session.execute(stmt).all()
            return set(rows)
        return _props_at

    @pytest.fixture
    def mems_at(self, session):
        def _mems_at(when):
            stmt = select(Membership).where(Membership.active_during.contains(when))
            return {m for m, *_ in session.execute(stmt).all()}
        return _mems_at

    def test_beginning(self, session, mems_at, props_at, mem1):
        when = _iso('2000-01-01')
        assert mems_at(when) == {mem1}
        assert props_at(when) \
               == {('good', False), ('other', False)}

    def test_right_at_new_membership(self, mems_at, props_at, mem1, mem2):
        when = _iso('2000-01-02')
        assert mems_at(when) == {mem1, mem2}
        assert props_at(when) \
               == {('bad', False), ('other', False),
                   ('good', True)}  # 'good' has beed denied

    def test_one_ended(self, mems_at, props_at, mem2):
        when = _iso('2000-01-03')
        assert mems_at(when) == {mem2}
        # 'good' has beed denied – but never granted, so it does not show up in the list!
        assert props_at(when) \
               == {('bad', False)}

    def test_right_after(self, mems_at, props_at):
        when = _iso('2000-01-04')
        assert mems_at(when) == set()
        assert props_at(when) == set()
