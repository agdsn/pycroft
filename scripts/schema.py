from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from pkg_resources import resource_filename


class AlembicHelper:
    def __init__(self, connection, config_file=None):
        self.connection = connection
        if config_file is None:
            config_file = resource_filename("pycroft.model", "alembic.ini")
        config = Config(config_file)
        self.scr = ScriptDirectory.from_config(config)
        self.context = self._new_context()
        self.running_version = self._get_running_version()
        self.desired_version = self._get_desired_version()

    def _new_context(self, **kwargs):
        return MigrationContext.configure(connection=self.connection, **kwargs)

    def _get_running_version(self):
        return self.context.get_current_revision()

    def _get_desired_version(self):
        return self.scr.get_current_head()
