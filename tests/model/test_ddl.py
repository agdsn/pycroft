import sqlalchemy.dialects.postgresql.base as postgresql_base
from sqlalchemy import PrimaryKeyConstraint, Table, Column, Integer, MetaData, \
    select, text, util
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import sqltypes

from pycroft.model.ddl import DropConstraint, CreateFunction, Function, View, \
    CreateView, DropView, Rule, CreateRule, ConstraintTrigger, \
    CreateConstraintTrigger, Trigger, CreateTrigger


class LiteralInterval(postgresql_base.INTERVAL):
    @classmethod
    def _adapt_from_generic_interval(cls, interval):
        return LiteralInterval(precision=interval.second_precision)

    def literal_processor(self, dialect):
        def process(value):
            return "interval '{}'".format(value) \
                .replace(',', '').replace(' 0:00:00', '')

        return process


class LiteralDate(postgresql_base.DATE):
    def literal_processor(self, dialect):
        def process(value):
            return "date '{}'".format(value.isoformat())

        return process


class Literal_PGDialect_pygresql(postgresql.dialect):
    colspecs = util.update_copy(
        postgresql.dialect.colspecs,
        {
            sqltypes.Interval: LiteralInterval,
            sqltypes.Date: LiteralDate,
        }
    )


def literal_compile(stmt):
    return str(stmt.compile(compile_kwargs={"literal_binds": True},
                            dialect=Literal_PGDialect_pygresql()))


def create_table(name):
    return Table(name, MetaData(), Column("id", Integer))


class TestConstraint:
    def test_drop_constraint_if_exists(self):
        table = create_table("test")
        stmt = DropConstraint(
            PrimaryKeyConstraint(table.c.id, name="pk_constraint"),
            if_exists=True)
        assert literal_compile(stmt) == "ALTER TABLE test DROP CONSTRAINT IF EXISTS pk_constraint"

    def test_drop_constraint_identifier_quotation(self):
        table = create_table("TABLE")
        stmt = DropConstraint(PrimaryKeyConstraint(table.c.id, name='PRIMARY'))
        assert literal_compile(stmt) == 'ALTER TABLE "TABLE" DROP CONSTRAINT "PRIMARY"'


class TestFunction:
    def test_create_function(self):
        func = Function("do_foo", [], "INTEGER", "BEGIN; RETURN NULL; END;")
        stmt = CreateFunction(func)
        assert literal_compile(stmt) == (
            'CREATE FUNCTION do_foo() '
            'RETURNS INTEGER VOLATILE LANGUAGE sql AS $$\n'
            'BEGIN; RETURN NULL; END;\n'
            '$$'
        )

    def test_create_function_with_quoting(self):
        func = Function("do foo", [], "INTEGER", "BEGIN; RETURN NULL; END;")
        stmt = CreateFunction(func)
        assert literal_compile(stmt) == (
            'CREATE FUNCTION "do foo"() '
            'RETURNS INTEGER VOLATILE LANGUAGE sql AS $$\n'
            'BEGIN; RETURN NULL; END;\n'
            '$$'
        )


class TestTrigger:
    def test_create_constraint_trigger(self):
        table = create_table("test")
        trigger = ConstraintTrigger("test_trigger", table, "INSERT", "do_foo()")
        stmt = CreateConstraintTrigger(trigger)
        assert literal_compile(stmt) == (
            'CREATE CONSTRAINT TRIGGER test_trigger '
            'AFTER I OR N OR S OR E OR R OR T '
            'ON test FOR EACH ROW EXECUTE PROCEDURE '
            'do_foo()'
        )

    def test_create_trigger(self):
        table = create_table("test")
        trigger = Trigger("test_trigger", table, "INSERT", "do_foo()")
        stmt = CreateTrigger(trigger)
        assert literal_compile(stmt) == (
            'CREATE TRIGGER test_trigger '
            'AFTER I OR N OR S OR E OR R OR T '
            'ON test FOR EACH ROW EXECUTE PROCEDURE '
            'do_foo()'
        )


class TestRule:
    def test_create_rule(self):
        table = create_table("test")
        rule = Rule("test_select", table, "SELECT", "NOTHING")
        stmt = CreateRule(rule)
        assert literal_compile(stmt) == (
            'CREATE RULE test_select AS ON SELECT TO test '
            'DO NOTHING'
        )

    def test_create_or_replace_rule(self):
        table = create_table("test")
        rule = Rule("test_select", table, "SELECT", "NOTHING", do_instead=True)
        stmt = CreateRule(rule, or_replace=True)
        assert literal_compile(stmt) == (
            'CREATE OR REPLACE RULE test_select AS ON SELECT '
            'TO test DO INSTEAD NOTHING'
        )

    def test_create_instead_rule(self):
        table = create_table("test")
        rule = Rule("test_select", table, "SELECT", "NOTHING", do_instead=True)
        stmt = CreateRule(rule)
        assert literal_compile(stmt) == (
            'CREATE RULE test_select AS ON SELECT TO test '
            'DO INSTEAD NOTHING'
        )

    def test_create_insert_rule(self):
        table1 = create_table("test")
        table2 = create_table("other")
        rule = Rule("test_insert", table1, "INSERT",
                    table2.insert().values(id=text("NEW.id")))
        stmt = CreateRule(rule)
        assert literal_compile(stmt) == (
            'CREATE RULE test_insert AS ON INSERT TO test '
            'DO INSERT INTO other (id) VALUES (NEW.id)'
        )

    def test_create_multiple_command_rule(self):
        table1 = create_table("test")
        table2 = create_table("other")
        table3 = create_table("yet_other")
        rule = Rule("test_insert", table1, "INSERT", [
            table2.insert().values(id=text("NEW.id")),
            table3.insert().values(id=text("NEW.id")),
        ])
        stmt = CreateRule(rule)
        assert literal_compile(stmt) == (
            'CREATE RULE test_insert AS ON INSERT TO test '
            'DO ('
            'INSERT INTO other (id) VALUES (NEW.id); '
            'INSERT INTO yet_other (id) VALUES (NEW.id)'
            ')'
        )

    def test_create_update_rule(self):
        table1 = create_table("test")
        table2 = create_table("other")
        rule = Rule("test_update", table1, "UPDATE",
                    table2.update().values(id=text("NEW.id")))
        stmt = CreateRule(rule)
        assert literal_compile(stmt) == (
            'CREATE RULE test_update AS ON UPDATE TO test '
            'DO UPDATE other SET id=NEW.id'
        )

    def test_create_delete_rule(self):
        table1 = create_table("test")
        table2 = create_table("other")
        rule = Rule("test_delete", table1, "DELETE", table2.delete())
        stmt = CreateRule(rule)
        assert literal_compile(stmt) == (
            'CREATE RULE test_delete AS ON DELETE TO test '
            'DO DELETE FROM other'
        )


class TestView:
    def test_plain_create_view(self):
        table = create_table("table")
        view = View("view", select([table.c.id]))
        stmt = CreateView(view)
        assert literal_compile(stmt) == (
            'CREATE VIEW view AS SELECT "table".id \n'
            'FROM "table"'
        )

    def test_create_or_replace_view(self):
        table = create_table("table")
        view = View("view", select([table.c.id]))
        stmt = CreateView(view, or_replace=True)
        assert literal_compile(stmt) == (
            'CREATE OR REPLACE VIEW view AS SELECT "table".id \n'
            'FROM "table"'
        )

    def test_create_temporary_view(self):
        table = create_table("table")
        view = View("view", select([table.c.id]), temporary=True)
        stmt = CreateView(view)
        assert literal_compile(stmt) == (
            'CREATE TEMPORARY VIEW view AS SELECT "table".id \n'
            'FROM "table"'
        )

    def test_create_view_with_view_options(self):
        table = create_table("table")
        view = View("view", select([table.c.id]), view_options=[
            ('check_option', 'cascaded'),
            ('security_barrier', 't'),
        ])
        stmt = CreateView(view)
        assert literal_compile(stmt) == (
            'CREATE VIEW view '
            'WITH (check_option = cascaded, security_barrier = t) '
            'AS SELECT "table".id \n'
            'FROM "table"'
        )

    def test_create_view_with_check_option(self):
        table = create_table("table")
        view = View("view", select([table.c.id]), check_option='cascaded')
        stmt = CreateView(view)
        assert literal_compile(stmt) == (
            'CREATE VIEW view '
            'AS SELECT "table".id \n'
            'FROM "table" '
            'WITH CASCADED CHECK OPTION'
        )

    def test_drop_view(self):
        table = create_table("table")
        view = View("view", select([table.c.id]))
        stmt = DropView(view)
        assert literal_compile(stmt) == (
            'DROP VIEW view'
        )

    def test_drop_view_if_exists(self):
        table = create_table("table")
        view = View("view", select([table.c.id]))
        stmt = DropView(view, if_exists=True)
        assert literal_compile(stmt) == (
            'DROP VIEW IF EXISTS view'
        )

    def test_drop_view_cascade(self):
        table = create_table("table")
        view = View("view", select([table.c.id]))
        stmt = DropView(view, cascade=True)
        assert literal_compile(stmt) == (
            'DROP VIEW view CASCADE'
        )
