"""
pycroft.lib.stats
~~~~~~~~~~~~~~~~~
"""
from dataclasses import dataclass

from sqlalchemy import func

from pycroft import config
from pycroft.model.finance import Split
from pycroft.model.user import PreMember, User, Membership


@dataclass
class OverviewStats:
    member_requests: int
    users_in_db: int
    members: int
    not_paid_all: int
    not_paid_members: int


def overview_stats() -> OverviewStats:
    return OverviewStats(
        member_requests=PreMember.q.count(),
        users_in_db=User.q.count(),
        members=User.q
            .join(Membership)
            .filter(Membership.group == config.member_group,
                    Membership.active_during.contains(func.current_timestamp()))
            .count(),
        not_paid_all=User.q
            .join(User.account)
            .join(Split)
            .group_by(User.id)
            .having(func.sum(Split.amount) > 0)
            .count(),
        not_paid_members=User.q
            .join(Membership)
            .filter(Membership.group == config.member_group,
                    Membership.active_during.contains(func.current_timestamp()))
            .join(User.account)
            .join(Split)
            .group_by(User.id)
            .having(func.sum(Split.amount) > 0)
            .count(),
    )
