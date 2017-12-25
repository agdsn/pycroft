import factory

from pycroft.model.user import Membership

from .base import BaseFactory
from .user import UserFactory

class MembershipFactory(BaseFactory):
    class Meta:
        model = Membership
    begins_at = None
    ends_at = None

    user = factory.SubFactory(UserFactory)
    # note: group is non-nullable!
    group = None
