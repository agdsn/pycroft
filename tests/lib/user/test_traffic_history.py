from datetime import datetime, timedelta

from pycroft.lib.user import traffic_history
from tests.legacy_base import FactoryDataTestBase
from tests.factories import TrafficVolumeLastWeekFactory, UserWithHostFactory


class TestTrafficHistory(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.user = UserWithHostFactory()
        TrafficVolumeLastWeekFactory.create_batch(7,
                                                  ip=self.user.hosts[0].interfaces[0].ips[0],
                                                  user=self.user)

    def test_get_traffic_history(self):
        history = traffic_history(self.user.id, datetime.now() - timedelta(7), datetime.now())
        assert len(history) == 8
        assert sum(t.egress + t.ingress for t in history) > 0


    def test_get_traffic_history_longer(self):
        history = traffic_history(self.user.id, datetime.now() - timedelta(14), datetime.now())
        assert len(history) == 15
        assert [(t.egress, t.ingress) for t in history[:7]] == [(0, 0)] * 7
