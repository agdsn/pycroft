import os
import re
from functools import partial
from io import StringIO

import pytest

from scripts.schema import AlembicHelper, SchemaStrategist


class MockedStrategist(SchemaStrategist):
    run = 'run'
    upgrade = 'upgrade'
    manual_intervention = 'manual'
    create_then_stamp = 'create'


class EmptyDBStrategist(MockedStrategist):
    """A Strategist who always assumes the db to be empty"""
    @staticmethod
    def db_filled_heuristic(*a, **kw):
        return False


@pytest.fixture
def helper(connection) -> AlembicHelper:
    return AlembicHelper(connection)


@pytest.mark.usefixtures("session")
class TestSchemaStrategy:
    def test_we_have_a_revision(self, helper):
        assert helper.desired_version

    def test_default_wants_intervention(self, helper):
        strategist = MockedStrategist(helper)
        assert (
            strategist.determine_schema_strategy()
            == MockedStrategist.manual_intervention
        )

    def test_empty_database_will_create(self, helper):
        strategist = EmptyDBStrategist(helper)
        assert (
            strategist.determine_schema_strategy() == MockedStrategist.create_then_stamp
        )

    def test_stamped_schema_is_ok(self, helper, connection, session):
        helper.stamp()
        # self.helper sticks to the old versions
        helper = AlembicHelper(connection)
        assert helper.running_version
        assert helper.running_version == helper.desired_version
        strategist = MockedStrategist(helper)
        assert strategist.determine_schema_strategy() == strategist.run

    def test_old_schema_needs_upgrade(self, helper, connection):
        helper.stamp(revision="4784a128a6dd")  # something != the head revision
        helper = AlembicHelper(connection)
        strategist = MockedStrategist(helper)
        assert strategist.determine_schema_strategy() == strategist.upgrade


class TestUpgrade:
    @staticmethod
    def create_revision(msg, request) -> str:
        """Create an empty alembic revision with a given message

        The created revision files will be removed afterwards.
        Although it would be cleaner to use a separate directory for
        the version locations, the `alembic` CLI requires a separate
        config file for that, so this is the more pragmatic approach.
        """
        from alembic.config import main as alembic_main
        from contextlib import redirect_stdout

        f = StringIO()
        os.chdir("pycroft/model")
        with redirect_stdout(f):
            res = alembic_main(argv=("revision", "-m", msg), prog="alembic")
        out = f.getvalue()
        os.chdir("../..")

        if res:
            pytest.fail(f"`alembic revision` returned a nonzero exit code:{res=}")

        created_files = re.findall(r"Generating (.*?\.py)", out)
        for created_file in created_files:
            pass
            request.addfinalizer(partial(os.remove, created_file))
        return out

    def test_schema_upgrade(self, request, helper, connection):
        self.create_revision("Initial Testrevision", request)
        helper.stamp()
        initial_version = helper.running_version

        out = self.create_revision("Testrevision", request)
        assert "Generating /" in out
        assert "_testrevision.py" in out

        new_created_version = helper.desired_version
        assert new_created_version != initial_version

        helper.upgrade()
        new_running_version = helper._get_running_version()
        assert new_running_version == new_created_version
