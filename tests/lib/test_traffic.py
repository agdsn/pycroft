# TODO: Tests for traffic history
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from pycroft.lib.traffic import delete_old_traffic_data
from pycroft.model.host import Interface
from tests import factories as f


@pytest.fixture(scope="module")
def interface(module_session: Session):
    i = f.InterfaceFactory()
    module_session.flush()
    return i


@pytest.mark.parametrize(
    "age_days, old",
    (
        *[(d, False) for d in range(8)],
        *[(d, True) for d in range(8, 20)],
    ),
)
def test_traffic_volume_cleanup(
    session, interface: Interface, age_days: int, old: bool
):
    f.TrafficVolumeFactory(
        timestamp=datetime.utcnow() - timedelta(age_days),
        ip__interface=interface,
    )
    session.flush()
    num_deleted = delete_old_traffic_data(session)
    assert 0 <= num_deleted <= 1
    got_deleted = num_deleted == 1

    if old:
        assert (
            got_deleted
        ), f"Traffic volume from {age_days} days ago didn't get deleted in cleanup"
    else:
        assert (
            not got_deleted
        ), f"Traffic volume from {age_days} days ago unexpectedly got deleted in cleanup"
