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
