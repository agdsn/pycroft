from datetime import datetime, timedelta, timezone
from functools import partial
from itertools import chain

import factory

from pycroft.model.user import Membership, PropertyGroup
from pycroft.helpers import interval

from .base import BaseFactory
from .user import UserFactory


class MembershipFactory(BaseFactory):
    class Meta:
        model = Membership
        exclude = ('begins_at', 'ends_at')
    begins_at = datetime.now(timezone.utc)
    ends_at = None
    active_during = interval.closedopen(begins_at, ends_at)

    user = factory.SubFactory(UserFactory)
    # note: group is non-nullable!
    group = None

    class Params:
        includes_today = factory.Trait(
            active_during=interval.closedopen(
                datetime.now(timezone.utc) - timedelta(1),
                datetime.now(timezone.utc) + timedelta(1),
            ),
        )


def _maybe_append_seq(n, prefix):
    """Append a sequence value to a prefix if non-zero"""
    if not n:
        return prefix
    return "{} {}".format(prefix, n)


class PropertyGroupFactory(BaseFactory):
    class Meta:
        model = PropertyGroup
        exclude = ('granted', 'denied')
    granted = frozenset()
    denied = frozenset()

    name = factory.Sequence(lambda n: "Property group %s" % n)
    permission_level = factory.LazyAttribute(lambda _: 0)

    @factory.lazy_attribute
    def property_grants(self):
        return dict(chain(((k, True) for k in self.granted),
                          ((k, False) for k in self.denied)))


class AdminPropertyGroupFactory(PropertyGroupFactory):
    name = factory.Sequence(partial(_maybe_append_seq, prefix="Admin-Gruppe"))
    granted = frozenset((
        'user_show', 'user_change', 'user_mac_change',
        'infrastructure_show', 'infrastructure_change',
        'facilities_show', 'facilities_change',
        'groups_show', 'groups_change_membership', 'groups_change',
    ))
    permission_level = 10


class FinancePropertyGroupFactory(PropertyGroupFactory):
    name = factory.Sequence(partial(_maybe_append_seq, prefix="Finanzer-Gruppe"))
    granted = frozenset(('finance_show', 'finance_change'))
    permission_level = 80


class MemberPropertyGroupFactory(PropertyGroupFactory):
    name = factory.Sequence(partial(_maybe_append_seq, prefix="Mitglied-Gruppe"))
    granted = frozenset((
        'ldap', 'ldap_login_enabled', 'mail', 'member', 'membership_fee',
        'network_access', 'userdb', 'userwww'
    ))
