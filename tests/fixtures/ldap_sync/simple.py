from datetime import datetime, timedelta

from fixture import DataSet

from tests.fixtures.dummy.unixaccount import UserData
from tests.fixtures.dummy.property import PropertyGroupData


class MembershipData(DataSet):
    class dummy_membership:
        begins_at = datetime.utcnow() - timedelta(1)
        ends_at = datetime.utcnow() + timedelta(1)
        group = PropertyGroupData.dummy
        user = UserData.withldap


class PropertyData(DataSet):
    class mail:
        property_group = PropertyGroupData.dummy
        name = "mail"
        granted = True


# This is a simple fixture providing dummy users, one of which has a
# unix_account.  This user is member in a propertygroup granted the property
# ``mail``: ``UserData.withldap.has_property('mail')``
datasets = frozenset([PropertyData, MembershipData])
