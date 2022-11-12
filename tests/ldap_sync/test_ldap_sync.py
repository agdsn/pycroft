# pylint: disable=missing-docstring

import ldap3
import pytest

from ldap_sync.concepts import types
from ldap_sync.concepts.action import (
    AddAction,
    IdleAction,
    DeleteAction,
    ModifyAction,
    Action,
)
from ldap_sync.concepts.record import UserRecord, GroupRecord
from ldap_sync.conversion import (
    dn_from_cn,
    dn_from_username,
    db_user_to_record,
)
from ldap_sync.execution import execute_real
from ldap_sync.record_diff import bulk_diff_records
from ldap_sync.sources.db import (
    _fetch_db_users,
    _fetch_db_groups,
    _fetch_db_properties,
    fetch_db_users,
    fetch_db_groups,
    fetch_db_properties,
)
from ldap_sync.sources.ldap import (
    _fetch_ldap_users,
    fetch_ldap_groups,
    fetch_ldap_properties,
    fetch_ldap_users,
)
from pycroft.model.user import PropertyGroup, User
from tests.factories import PropertyGroupFactory, UserFactory, MembershipFactory
from tests.ldap_sync import _cleanup_conn


class TestEmptyLdap:
    @pytest.fixture(scope='class')
    def desired_user(self):
        return UserRecord(dn=types.DN("user"), attrs={})


@pytest.mark.usefixtures("muted_ldap_logger")
class TestEmptyDatabase:
    @pytest.fixture(scope="class", autouse=True)
    def users(self, class_session):
        return UserFactory.create_batch(5)

    def test_no_users_fetched(self, session):
        assert _fetch_db_users(session) == []


class TestOneUserFetch:
    PROPNAME = 'mail'

    @pytest.fixture(scope="class")
    def propgroup(self, class_session) -> PropertyGroup:
        return PropertyGroupFactory.create(
            name="my propgroup",
            granted={self.PROPNAME, 'ldap_login_enabled'}
        )

    @pytest.fixture(scope="class", autouse=True)
    def user(self, class_session, propgroup) -> User:
        return UserFactory.create(
            name="Hans Wurst", login="hans",
            with_membership=True,
            membership__group=propgroup,
            membership__includes_today=True,
            with_unix_account=True,
        )

    def test_one_user_fetched(self, session):
        users = _fetch_db_users(session, required_property=self.PROPNAME)
        assert len(users) == 1, f"Not a list of length one: {users}"

    def test_one_group_fetched(self, session, propgroup, user):
        groups = [
            group
            for group in _fetch_db_groups(session)
            if group.Group.name == propgroup.name
        ]
        assert len(groups) == 1
        assert set(groups[0].members) == {user.login}

    def test_one_property_fetched(self, session, user):
        properties = [
            prop for prop in _fetch_db_properties(session) if prop.name == self.PROPNAME
        ]
        assert len(properties) == 1
        assert set(properties[0].members) == {user.login}


class TestMultipleUsersFilter:
    @pytest.fixture(scope="class")
    def propgroup(self, class_session) -> PropertyGroup:
        return PropertyGroupFactory.create(
            name="my property group",
            granted={'mail', 'ldap_login_enabled'},
        )

    @pytest.fixture(scope="class")
    def users(self, class_session, propgroup) -> tuple[User, User]:
        return UserFactory.create_batch(
            2,
            with_membership=True,
            membership__group=propgroup,
            membership__includes_today=True,
            with_unix_account=True,
        )

    def test_correct_users_fetched(self, session, users):
        user1, user2 = users
        users = _fetch_db_users(session, required_property="mail")
        expected_logins = {user1.login, user2.login}
        assert {u.User.login for u in users} == expected_logins


def test_ldap_base_exists(conn, clean_ldap_base, sync_config):
    success = conn.search(sync_config.base_dn, "(objectclass=*)", ldap3.BASE)
    assert success, f"Base DN search failed: {conn.result}"


def test_adding_an_entry_works(conn, clean_ldap_base, sync_config):
    base_dn = sync_config.base_dn
    conn.add(f"uid=bar,{base_dn}", ["inetOrgPerson"], {"sn": "test", "cn": "test"})
    assert conn.search(
        base_dn, "(objectclass=inetOrgPerson)"
    ), f"Base DN subtree search failed: {conn.result}"
    relevant_entries = [r for r in conn.response if r["dn"] != base_dn]
    assert len(relevant_entries) == 1


@pytest.mark.usefixtures("clean_ldap_base")
class LdapSyncerTestBase:
    @pytest.fixture(scope="class", autouse=True)
    def users(self, class_session):
        u1, u2 = UserFactory.create_batch(2, with_unix_account=True)
        inconsistent = UserFactory.create(with_unix_account=True, email=None)

        p_dummy = PropertyGroupFactory.create(name='group_without_grants')
        pg_member = PropertyGroupFactory.create(name='member',
                                                granted={'mail', 'ldap_login_enabled'})

        UserFactory.create(with_membership=True, membership__group=p_dummy, with_unix_account=True)
        for user in [u1, u2, inconsistent]:
            MembershipFactory.create(group=pg_member, user=user)

        MembershipFactory.create(
            user=inconsistent,
            group=PropertyGroupFactory.create(
                name='some_weird_group',
                granted={'mail'},  # weird, because grants mail, but not ldap_login_enabled
            ),
        )

    @pytest.fixture(scope="class")
    def class_conn(self, get_connection) -> ldap3.Connection:
        with get_connection() as conn:
            yield conn
        _cleanup_conn(conn)

    @pytest.fixture(scope="class")
    def user_records_to_sync(
        self, class_session, sync_config, users
    ) -> list[UserRecord]:
        return list(
            fetch_db_users(
                class_session, sync_config.user_base_dn, sync_config.required_property
            )
        )

    @pytest.fixture(scope="class")
    def initial_ldap_user_records(self, class_conn, sync_config) -> list[UserRecord]:
        return list(fetch_ldap_users(class_conn, base_dn=sync_config.user_base_dn))

    @pytest.fixture(scope="class")
    def group_records_to_sync(
        self, class_session, sync_config, users
    ) -> list[GroupRecord]:
        return list(
            fetch_db_groups(
                class_session,
                base_dn=sync_config.group_base_dn,
                user_base_dn=sync_config.user_base_dn,
            )
        )

    @pytest.fixture(scope="class")
    def initial_ldap_group_records(self, class_conn, sync_config) -> list[GroupRecord]:
        return list(fetch_ldap_groups(class_conn, base_dn=sync_config.group_base_dn))

    @pytest.fixture(scope="class")
    def property_records_to_sync(
        self, class_session, sync_config, users
    ) -> list[GroupRecord]:
        return list(
            fetch_db_properties(
                session=class_session,
                base_dn=sync_config.property_base_dn,
                user_base_dn=sync_config.user_base_dn,
            )
        )

    @pytest.fixture(scope="class")
    def initial_ldap_property_records(
        self, class_conn, sync_config
    ) -> list[GroupRecord]:
        return list(
            fetch_ldap_properties(class_conn, base_dn=sync_config.property_base_dn)
        )

    @pytest.fixture(scope="class")
    def actions(
        self,
        initial_ldap_user_records,
        initial_ldap_group_records,
        initial_ldap_property_records,
        user_records_to_sync,
        group_records_to_sync,
        property_records_to_sync,
    ) -> list[Action]:
        return [
            *bulk_diff_records(
                initial_ldap_user_records, user_records_to_sync
            ).values(),
            *bulk_diff_records(
                initial_ldap_group_records, group_records_to_sync
            ).values(),
            *bulk_diff_records(
                initial_ldap_property_records, property_records_to_sync
            ).values(),
        ]

    @pytest.fixture(scope="class")
    def sync_all(self, actions):
        def sync_all(conn: ldap3.Connection):
            # TODO this is broken.
            #  In this sort of integration test, we want `sync_all` to fetch and sync,
            #  not only sync.
            for a in actions:
                execute_real(a, conn)

        return sync_all

    @classmethod
    def get_by_dn(cls, ldap_records, dn: types.DN):
        return next(u for u in ldap_records if u.dn == dn)


class TestInitialSync(LdapSyncerTestBase):
    @pytest.mark.meta
    def test_connection_works(self, conn, sync_config):
        assert conn.bound
        assert conn.search(sync_config.base_dn, "(objectclass=*)", ldap3.BASE)

    @pytest.mark.meta
    def test_initial_state(
        self,
        initial_ldap_user_records,
        initial_ldap_group_records,
        initial_ldap_property_records,
    ):
        assert initial_ldap_user_records == []
        assert initial_ldap_group_records == []
        assert initial_ldap_property_records == []

    @pytest.fixture
    def assert_entries_synced(
        self,
        conn,
        sync_config,
        user_records_to_sync,
        group_records_to_sync,
        property_records_to_sync,
    ):
        def assert_entries_synced():
            new_users = list(fetch_ldap_users(conn, base_dn=sync_config.user_base_dn))
            assert len(new_users) == len(user_records_to_sync)
            new_groups = list(
                fetch_ldap_groups(conn, base_dn=sync_config.group_base_dn)
            )
            assert len(new_groups) == len(group_records_to_sync)
            new_properties = list(
                fetch_ldap_properties(conn, base_dn=sync_config.property_base_dn)
            )
            assert len(new_properties) == len(property_records_to_sync)

        return assert_entries_synced

    def test_syncall_adds_entries(self, conn, sync_all, assert_entries_synced):
        sync_all(conn)
        assert_entries_synced()

    def test_exporter_compiles_all_addactions(
        self,
        conn,
        actions,
        user_records_to_sync,
        group_records_to_sync,
        property_records_to_sync,
        assert_entries_synced,
    ):
        assert len(actions) == sum(
            (
                len(user_records_to_sync),
                len(group_records_to_sync),
                len(property_records_to_sync),
            )
        )
        assert (isinstance(a, AddAction) for a in actions)

        for a in actions:
            return execute_real(a, conn)
        assert_entries_synced()


class TestLdapSyncerOnceSynced(LdapSyncerTestBase):
    @pytest.fixture(autouse=True)
    def once_synced(self, class_conn, sync_all, clean_ldap_base) -> None:
        sync_all(class_conn)

    @pytest.fixture
    def new_ldap_user_records(self, class_conn, sync_config, once_synced):
        users = list(fetch_ldap_users(class_conn, sync_config.user_base_dn))
        return users

    @pytest.fixture
    def new_ldap_group_records(self, class_conn, sync_config, once_synced):
        return list(fetch_ldap_groups(class_conn, sync_config.group_base_dn))

    @pytest.fixture
    def new_ldap_property_records(self, class_conn, sync_config, once_synced):
        return list(fetch_ldap_properties(class_conn, sync_config.property_base_dn))

    def test_idempotency_of_two_syncs(
        self,
        new_ldap_user_records,
        new_ldap_property_records,
        new_ldap_group_records,
        user_records_to_sync,
        group_records_to_sync,
        property_records_to_sync,
    ):
        actions = [
            *bulk_diff_records(new_ldap_user_records, user_records_to_sync).values(),
            *bulk_diff_records(new_ldap_group_records, group_records_to_sync).values(),
            *bulk_diff_records(
                new_ldap_property_records, property_records_to_sync
            ).values(),
        ]
        assert len(actions) == sum(
            [
                len(user_records_to_sync),
                len(group_records_to_sync),
                len(property_records_to_sync),
            ]
        )
        assert all([isinstance(a, IdleAction) for a in actions])

    def test_user_attributes_synced_correctly(
        self, user_records_to_sync, new_ldap_user_records
    ):
        records = {r.dn: r for r in user_records_to_sync}
        for ldap_record in new_ldap_user_records:
            assert_attributes_equal(records[ldap_record.dn], ldap_record)

    @pytest.fixture(scope="class")
    def filter_members(self, user_records_to_sync):
        def filter_members(members):
            """Remove users that are not exported."""
            return [
                m
                for m in members
                if any(u.attrs["uid"] == m for u in user_records_to_sync)
            ]

        return filter_members

    @pytest.fixture(scope="class")
    def with_members_filtered(self, filter_members):
        def with_members_filtered(record):
            record.attrs["member"] = filter_members(record.attrs["member"])
            return record

        return with_members_filtered

    def test_group_attributes_synced_correctly(
        self, group_records_to_sync, new_ldap_group_records, with_members_filtered
    ):
        records: dict[types.DN, GroupRecord] = {
            r.dn: with_members_filtered(r) for r in group_records_to_sync
        }
        for ldap_record in new_ldap_group_records:
            assert_attributes_equal(records[ldap_record.dn], ldap_record)

    def test_property_attributes_synced_correctly(
        self, property_records_to_sync, new_ldap_property_records, with_members_filtered
    ):
        records = {r.dn: with_members_filtered(r) for r in property_records_to_sync}
        for ldap_record in new_ldap_property_records:
            assert_attributes_equal(records[ldap_record.dn], ldap_record)

    def test_mail_deletion(self, conn, session, sync_config, sync_all):
        users_with_mail = [
            u
            for u in _fetch_db_users(session, sync_config.required_property)
            if u.User.email is not None
        ]
        if not users_with_mail:
            raise RuntimeError("Fixtures do not provide a syncable user with a mail address")

        modified_user = users_with_mail[0].User
        mod_dn = db_user_to_record(modified_user, sync_config.user_base_dn).dn
        print(f"Mail before: {modified_user.email=}")
        modified_user.email = "bar@agdsn.de"  # ????? How is this mail deletion?
        modified_user.email = None
        session.add(modified_user)
        session.flush()
        id = modified_user.id

        user_records_to_sync = list(
            fetch_db_users(
                session,
                sync_config.user_base_dn,
                sync_config.required_property,
            )
        )

        # breakpoint()
        # TODO: sync seems to be broken.
        # check `user_records_to_sync` for presence of `modified_user`; mail should be empty.
        # TODO: we need to _inject_ the `user_records_to_sync` method… it's partial now…
        # perhaps a workaround would be to call the outer API instead of diffing manually…
        sync_all(conn)

        modified_user = next(
            r
            for r in _fetch_ldap_users(conn, base_dn=sync_config.user_base_dn)
            if r["dn"] == mod_dn
        )
        assert "mail" not in modified_user

    def test_mail_creation(self, conn, session, sync_config, new_ldap_user_records):
        config = sync_config
        users_without_mail = [
            u
            for u in _fetch_db_users(session, config.required_property)
            if u.User.email is None
        ]
        if not users_without_mail:
            raise RuntimeError("Fixtures do not provide a syncable user without a mail address")
        mod_user = users_without_mail[0].User
        mod_dn = db_user_to_record(mod_user, sync_config.user_base_dn).dn
        mod_user.email = 'bar@agdsn.de'
        session.add(mod_user)
        session.flush()

        user_records_to_sync = list(
            fetch_db_users(session, sync_config.user_base_dn, config.required_property)
        )
        actions = list(
            bulk_diff_records(
                current=new_ldap_user_records, desired=user_records_to_sync
            ).values()
        )
        # we get 3 actions
        relevant_actions = [a for a in actions if not isinstance(a, IdleAction)]
        assert len(relevant_actions) == 1
        assert type(relevant_actions[0]) == ModifyAction
        for a in actions:
            execute_real(a, conn)

        newest_users = list(fetch_ldap_users(conn, base_dn=sync_config.user_base_dn))
        modified_ldap_record = self.get_by_dn(newest_users, mod_dn)
        assert modified_ldap_record.attrs.get("mail") == [mod_user.email]

    @pytest.mark.xfail(
        reason="This test is broken."
        " It isn't an integration test because the membership change"
        " is never persisted into the database."
    )
    def test_change_property_membership(self):
        mail_property = next(
            p for p in _fetch_db_properties(self.session) if p.name == "mail"
        )
        mail_property_dn = dn_from_cn(
            name=mail_property.name, base=self.property_base_dn
        )

        member = mail_property.members[0]
        member_dn = dn_from_username(member, self.user_base_dn)

        assert (
            member_dn
            in self.get_by_dn(self.new_ldap_property_records, mail_property_dn).attrs[
                "member"
            ]
        )

        mail_property.members.remove(member)
        self.initial_ldap_property_records = self.new_ldap_property_records
        self.sync_all()
        newest_ldap_properties = list(
            fetch_ldap_properties(self.conn, self.property_base_dn)
        )
        assert (
            member_dn
            not in self.get_by_dn(newest_ldap_properties, mail_property_dn).attrs[
                "member"
            ]
        )

        mail_property.members.append(member)
        self.initial_ldap_property_records = newest_ldap_properties
        self.sync_all()
        newest_ldap_properties = list(
            fetch_ldap_properties(self.conn, self.property_base_dn)
        )
        assert (
            member_dn
            in self.get_by_dn(newest_ldap_properties, mail_property_dn).atrs["member"]
        )

    def test_no_desired_records_removes_everything(
        self, conn, new_ldap_user_records, sync_config
    ):
        actions_dict = bulk_diff_records(current=new_ldap_user_records, desired=[])

        assert len(actions_dict) == len(new_ldap_user_records)
        for action in actions_dict.values():
            assert type(action) == DeleteAction

        for action in actions_dict.values():
            execute_real(action, conn)

        assert list(fetch_ldap_users(conn, base_dn=sync_config.user_base_dn)) == []


def assert_attributes_equal(expected, actual):
    # Due to the canonicalization, empty attributes will appear in
    # `expected`.  We want to ignore those for the comparison.
    effective_attributes_in_db = {
        key: val for key, val in expected.attrs.items() if val != []
    }
    assert effective_attributes_in_db == {
        k: v for k, v in actual.attrs.items() if k in effective_attributes_in_db
    }
