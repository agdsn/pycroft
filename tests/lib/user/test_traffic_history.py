from datetime import timedelta

import pytest

from pycroft.lib.user import traffic_history
from pycroft.model.user import User
from tests.factories import TrafficVolumeLastWeekFactory, UserFactory


class TestTrafficHistory:
    @pytest.fixture(scope="class")
    def user(self, class_session) -> User:
        return UserFactory(with_host=True)

    @pytest.fixture(scope="class", autouse=True)
    def traffic(self, class_session, user) -> None:
        TrafficVolumeLastWeekFactory.create_batch(
            7,
            ip=user.hosts[0].interfaces[0].ips[0],
            user=user
        )
        class_session.flush()

    def test_get_traffic_history(self, user, utcnow):
        history = traffic_history(user.id, utcnow - timedelta(7), utcnow)
        assert len(history) == 8
        assert sum(t.egress + t.ingress for t in history) > 0

    def test_get_traffic_history_longer(self, user, utcnow):
        history = traffic_history(user.id, utcnow - timedelta(14), utcnow)
        assert len(history) == 15
        assert [(t.egress, t.ingress) for t in history[:7]] == [(0, 0)] * 7
