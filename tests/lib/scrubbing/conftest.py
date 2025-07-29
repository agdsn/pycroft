import pytest
from sqlalchemy.orm import Session

from pycroft.model.user import PropertyGroup
from tests import factories as f


@pytest.fixture(scope="module")
def group_do_not_archive(module_session: Session) -> PropertyGroup:
    return f.PropertyGroupFactory.create(
        name="Do Not Archive Group", granted={"do-not-archive"}, denied=set()
    )


@pytest.fixture(autouse=True)
def freeze(freezer) -> None:
    freezer.move_to("2025-01-01")
