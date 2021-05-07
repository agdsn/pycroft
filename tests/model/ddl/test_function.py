from pycroft.model.ddl import Function, CreateFunction
from . import literal_compile


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
