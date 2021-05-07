from sqlalchemy import text

from pycroft.model.ddl import Rule, CreateRule
from . import create_table, literal_compile


class TestRule:
    def test_create_rule(self, table):
        rule = Rule("test_select", table, "SELECT", "NOTHING")
        stmt = CreateRule(rule)
        assert literal_compile(stmt) == (
            'CREATE RULE test_select AS ON SELECT TO test '
            'DO NOTHING'
        )

    def test_create_or_replace_rule(self, table):
        rule = Rule("test_select", table, "SELECT", "NOTHING", do_instead=True)
        stmt = CreateRule(rule, or_replace=True)
        assert literal_compile(stmt) == (
            'CREATE OR REPLACE RULE test_select AS ON SELECT '
            'TO test DO INSTEAD NOTHING'
        )

    def test_create_instead_rule(self, table):
        rule = Rule("test_select", table, "SELECT", "NOTHING", do_instead=True)
        stmt = CreateRule(rule)
        assert literal_compile(stmt) == (
            'CREATE RULE test_select AS ON SELECT TO test '
            'DO INSTEAD NOTHING'
        )

    def test_create_insert_rule(self, table, table2):
        rule = Rule("test_insert", table, "INSERT", table2.insert().values(id=text("NEW.id")))
        stmt = CreateRule(rule)
        assert literal_compile(stmt) == (
            'CREATE RULE test_insert AS ON INSERT TO test '
            'DO INSERT INTO test2 (id) VALUES (NEW.id)'
        )

    def test_create_multiple_command_rule(self, table, table2, table3):
        rule = Rule("test_insert", table, "INSERT", [
            table2.insert().values(id=text("NEW.id")),
            table3.insert().values(id=text("NEW.id")),
        ])
        stmt = CreateRule(rule)
        assert literal_compile(stmt) == (
            'CREATE RULE test_insert AS ON INSERT TO test '
            'DO ('
            'INSERT INTO test2 (id) VALUES (NEW.id); '
            'INSERT INTO test3 (id) VALUES (NEW.id)'
            ')'
        )

    def test_create_update_rule(self, table, table2):
        rule = Rule("test_update", table, "UPDATE", table2.update().values(id=text("NEW.id")))
        stmt = CreateRule(rule)
        assert literal_compile(stmt) == (
            'CREATE RULE test_update AS ON UPDATE TO test '
            'DO UPDATE test2 SET id=NEW.id'
        )

    def test_create_delete_rule(self, table, table2):
        rule = Rule("test_delete", table, "DELETE", table2.delete())
        stmt = CreateRule(rule)
        assert literal_compile(stmt) == (
            'CREATE RULE test_delete AS ON DELETE TO test '
            'DO DELETE FROM test2'
        )
