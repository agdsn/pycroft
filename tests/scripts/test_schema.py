import os
import re
import subprocess
from functools import partial
from tempfile import mkdtemp

from scripts.schema import AlembicHelper, SchemaStrategist
from tests import SQLAlchemyTestCase, get_engine_and_connection


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


class AlembicTest(SQLAlchemyTestCase):
    def setUp(self):
        super().setUp()
        _, self.connection = get_engine_and_connection()
        self.connection.execute("DROP TABLE alembic_version")
        self.helper = AlembicHelper(self.connection)


class TestSchemaStrategy(AlembicTest):
    def test_we_have_a_revision(self):
        self.assertTrue(self.helper.desired_version)

    def test_default_wants_intervention(self):
        strategist = MockedStrategist(self.helper)
        self.assertEqual(strategist.determine_schema_strategy(),
                         MockedStrategist.manual_intervention)

    def test_empty_database_will_create(self):
        strategist = EmptyDBStrategist(self.helper)
        self.assertEqual(strategist.determine_schema_strategy(),
                         MockedStrategist.create_then_stamp)

    def test_stamped_schema_is_ok(self):
        self.helper.stamp()
        # self.helper sticks to the old versions
        helper = AlembicHelper(self.connection)
        self.assertTrue(helper.running_version)
        self.assertEqual(helper.running_version, helper.desired_version)
        strategist = MockedStrategist(helper)
        self.assertEqual(strategist.determine_schema_strategy(),
                         strategist.run)

    def old_schema_needs_upgrade(self):
        self.helper.stamp(revision='aaaaaa')  # something != the head revision
        helper = AlembicHelper(self.connection)
        strategist = MockedStrategist(helper)
        self.assertEqual(strategist.determine_schema_strategy(),
                         strategist.upgrade)


class TestUpgrade(SQLAlchemyTestCase):
    def setUp(self):
        super().setUp()
        _, self.connection = get_engine_and_connection()

        # Patch AlembicHelper so it will use another location directory
        self.tmpdir = mkdtemp()

    def tearDown(self):
        os.rmdir(self.tmpdir)

    @property
    def helper(self):
        """Building a fresh helper every time

        This is convenient because every time e.g. a revision is added
        to our version directory, `helper.scr` does not know that.
        """
        return AlembicHelper(self.connection)

    def create_revision(self, msg):
        """Create an empty alembic revision with a given message

        The created revision files will be removed afterwards.
        Although it would be cleaner to use a separate directory for
        the version locations, the `alembic` CLI requires a separate
        config file for that, so this is the more pragmatic approach.
        """
        try:
            out = subprocess.check_output(["alembic", "revision", "-m", msg])
        except subprocess.CalledProcessError:
            self.fail("`alembic revision` returned a nonzero exit code.", )

        created_files = re.findall(r"Generating (.*?\.py)", out.decode('utf-8'))
        for created_file in created_files:
            self.addCleanup(partial(os.remove, created_file))
        return out


    def test_schema_upgrade(self):
        self.create_revision("Initial Testrevision")
        self.helper.stamp()
        initial_version = self.helper.running_version

        out = self.create_revision("Testrevision")
        self.assertIn(b"Generating /", out)
        self.assertIn(b"_testrevision.py", out)

        new_created_version = self.helper.desired_version
        self.assertNotEqual(new_created_version, initial_version)

        self.helper.upgrade()
        new_running_version = self.helper.running_version
        self.assertEqual(new_running_version, new_created_version)
