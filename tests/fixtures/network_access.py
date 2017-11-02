from datetime import datetime, timedelta

from fixture import DataSet

from tests.fixtures.dummy.user import UserData
from tests.fixtures.config import PropertyGroupData


class MembershipData(DataSet):
    """Provides a user `dummy` with network access"""
    class dummy_membership:
        begins_at = datetime.utcnow() - timedelta(1)
        ends_at = datetime.utcnow() + timedelta(1)
        group = PropertyGroupData.network_access
        user = UserData.dummy
