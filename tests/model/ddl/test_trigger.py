from pycroft.model.ddl import ConstraintTrigger, CreateConstraintTrigger, \
    Trigger, CreateTrigger
from . import create_table, literal_compile


class TestTrigger:
    def test_create_constraint_trigger(self, table):
        trigger = ConstraintTrigger("test_trigger", table, "INSERT", "do_foo()")
        stmt = CreateConstraintTrigger(trigger)
        assert literal_compile(stmt) == (
            'CREATE CONSTRAINT TRIGGER test_trigger '
            'AFTER I OR N OR S OR E OR R OR T '
            'ON test FOR EACH ROW EXECUTE PROCEDURE '
            'do_foo()'
        )

    def test_create_trigger(self, table):
        trigger = Trigger("test_trigger", table, "INSERT", "do_foo()")
        stmt = CreateTrigger(trigger)
        assert literal_compile(stmt) == (
            'CREATE TRIGGER test_trigger '
            'AFTER I OR N OR S OR E OR R OR T '
            'ON test FOR EACH ROW EXECUTE PROCEDURE '
            'do_foo()'
        )
