from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from pycroft.model import create_db_model


class AlembicHelper:
    def __init__(self, connection, config_file="./alembic.ini"):
        self.connection = connection
        config = Config(config_file)
        self.scr = ScriptDirectory.from_config(config)
        self.context = MigrationContext.configure(self.connection)
        self.running_version = self._get_running_version()
        self.desired_version = self._get_desired_version()

    def _get_running_version(self):
        return self.context.get_current_revision()

    def _get_desired_version(self):
        return self.scr.get_current_head()

    def stamp(self, revision='head'):
        self.context.stamp(self.scr, revision)


def db_has_nontrivial_objects(connection):
    # %% for escaping reasons: internally, %-Formatting is applied
    num_objects = connection.execute(
        "select count(*) from pg_class c"
        " join pg_namespace s on s.oid = c.relnamespace"
        " where s.nspname != 'information_schema'"
        " and s.nspname not like 'pg_%%'"
    ).scalar()
    return num_objects > 0


class SchemaStrategist:
    def __init__(self, helper):
        """create a new strategist

        :param AlembicHelper helper: Al helper to investigate the state of our
        alembic configuratior
        """
        self.helper = helper

    #: A function ``Connection -> : bool`` determining whether the
    #: schema can be assumed to be : empty.
    db_filled_heuristic = staticmethod(db_has_nontrivial_objects)

    def determine_schema_strategy(self):
        """Determine the strategy

        :param AlembicHelper state:
        """
        if self.helper.running_version == self.helper.desired_version:
            # Q: why is `run` run on an empty database?
            print("Determined strategy 'run'")
            return self.run
        if self.helper.running_version is not None:
            print("Determined strategy 'upgrade'")
            return self.upgrade
        if self.db_filled_heuristic(self.helper.connection):
            # db not empty, but not running version is None
            print("Determined strategy 'manual_intervention'")
            return self.manual_intervention
        print("Determined strategy 'create_then_stamp'")
        return self.create_then_stamp

    def run(self):
        print("Schema is up to date (revision: {})".format(self.helper.running_version))

    def upgrade(self):
        print("Schema is not up to date (current/desired: {}/{}). Please run an upgrade."
            .format(self.helper.running_version, self.helper.desired_version))
        exit(1)

    @staticmethod
    def manual_intervention():
        print("The database is filled, but not equipped with an alembic revision."
              " Please use an empty database or manually stamp it"
              " if you know what you're doing.")
        exit(1)

    def create_then_stamp(self):
        create_db_model(self.helper.connection)
        self.helper.stamp()
