import warnings as w

from alembic.config import Config
from alembic.operations.base import Operations
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from pkg_resources import resource_filename
from sqlalchemy import text


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

    def stamp(self, revision='head'):
        w.warn("do not use `AlembicHelper.run`", DeprecationWarning, stacklevel=2)
        self.context.stamp(self.scr, revision)

    def upgrade(self, revision='head', **kwargs):
        w.warn("do not use `AlembicHelper.upgrade`", DeprecationWarning, stacklevel=2)

        def upgrade(rev, context):
            # noinspection PyProtectedMember
            return self.scr._upgrade_revs(destination=revision, current_rev=rev)
        # early binding of the upgrade function (i.e., in self.ctx) is not possible because it is
        # bound to the target revision.
        upgrade_bound_ctx = self._new_context(opts={'fn': upgrade})
        # Configure alembic.op to use our upgrade context
        with Operations.context(upgrade_bound_ctx):
            with upgrade_bound_ctx.begin_transaction():
                upgrade_bound_ctx.run_migrations(**kwargs)

    def downgrade(self, revision, **kwargs):
        w.warn("do not use `AlembicHelper.downgrade`", DeprecationWarning, stacklevel=2)

        def downgrade(rev, context):
            # noinspection PyProtectedMember
            return self.scr._downgrade_revs(destination=revision, current_rev=rev)

        downgrade_bound_ctx = self._new_context(opts={'fn': downgrade})
        with Operations.context(downgrade_bound_ctx):
            with downgrade_bound_ctx.begin_transaction():
                downgrade_bound_ctx.run_migrations(**kwargs)


def db_has_nontrivial_objects(connection):
    # %% for escaping reasons: internally, %-Formatting is applied
    num_objects = connection.execute(text(
        "select count(*) from pg_class c"
        " join pg_namespace s on s.oid = c.relnamespace"
        " where (s.nspname = 'public' or s.nspname = 'pycroft')"
        " and s.nspname not like 'pg_%%'"
    )).scalar()
    return num_objects > 0

