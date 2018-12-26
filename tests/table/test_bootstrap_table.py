import re
from unittest import TestCase

from web.blueprints.helpers.table import Column, BootstrapTable, SplittedTable, \
    BootstrapTableMeta


class ColumnTestCase(TestCase):
    def test_init_requires_args(self):
        with self.assertRaises(TypeError):
            Column()  # pylint: disable=no-value-for-parameter

    def test_instatiation_with_name_and_title_works(self):
        c = Column(title="Test Column", name="test_col")
        self.assertEqual(c.name, "test_col")
        self.assertEqual(c.title, "Test Column")
        self.assertEqual(c.width, 0)
        self.assertEqual(c.cell_style, False)
        self.assertEqual(repr(c), "<Column 'test_col' title='Test Column'>")

    def test_instantiation_without_name(self):
        c = Column("Test Title")
        self.assertIsNone(c.name)
        self.assertEqual(c.title, "Test Title")


class InstantiatedColumnTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.column = Column(title="Test Column", name="test_col")

    def test_col_args(self):
        arg_string = self.column.build_col_args()
        self.assertIn('data-field="test_col"', arg_string)
        self.assertIn('data-sortable="true"', arg_string)

    def test_col_render(self):
        rendered = str(self.column)
        self.assertEqual(self.column.render(), rendered)
        self.assertTrue(rendered.startswith("<th"))
        self.assertTrue(rendered.endswith("</th>"))
        self.assertIn(self.column.build_col_args(), rendered)
        self.assertIn(self.column.title, rendered)


class CustomizedColumnTestCase(TestCase):
    def test_custom_arguments_set(self):
        rendered = str(Column(title="Test Column", name="test_col", width=3,
                              cell_style="customCellStyle"))
        self.assertIn('data-cell-style="customCellStyle"', rendered)
        self.assertIn('class="col-sm-3"', rendered)


class BootstrapTableTestCase(TestCase):
    def test_init_requires_args(self):
        with self.assertRaises(TypeError):
            BootstrapTable()  # pylint: disable=no-value-for-parameter

    def test_minimal_instantiation(self):
        t = BootstrapTable(data_url="http://foobar")
        self.assertEqual(t.columns, [])
        self.assertEqual(t.data_url, "http://foobar")
        self.assertEqual(repr(t), "<BootstrapTable cols=0 data_url='http://foobar'>")


class InstantiatedBootstrapTableTestCase(TestCase):
    def setUp(self):
        super().setUp()

        class Table(BootstrapTable):
            class Meta:
                table_args = {'foo': "bar", 'data-cache': "true"}
            col1 = Column("Column 1")
            col2 = Column("Column 2")

        self.Table = Table
        self.table = Table(data_url="http://dummy")

    def test_table_header_generation(self):
        header = self.table.table_header
        self.assertTrue(header.startswith("<thead><tr>"))
        self.assertTrue(header.endswith("</tr></thead>"))
        for col in self.table.columns:
            self.assertTrue(str(col))
            self.assertIn(str(col), header)

    def test_table_args_passed(self):
        self.assertEqual(self.table.table_args.get('data-cache'), "true")
        self.assertEqual(self.table.table_args.get('foo'), "bar")

    def test_table_args_parameter_take_precedence(self):
        table = self.Table(data_url="#", table_args={'foo': "new"})
        self.assertEqual(table.table_args['foo'], "new")

    def test_custom_table_args_will_be_used(self):
        self.table.table_args['special_arg'] = "someveryspecialargument"
        self.assertIn("someveryspecialargument", self.table.render("some-id"))

    def test_render_uses_the_generators_correctly(self):
        class MockedTable(BootstrapTable):
            def __init__(self):
                super().__init__(data_url="http://dummy")
            table_header = "HEADER"
            table_footer = "FOOTER"
            toolbar = "TOOLBAR"

        markup = MockedTable().render(table_id="TABLE_ID")
        TOOLBAR_RE = r'<div .*role="toolbar".*>\s*TOOLBAR\s*</div>'
        HEADER_RE = r'<table .*id="TABLE_ID".*>\s*HEADER\s*FOOTER\s*</table>'

        self.assertEqual(len(re.findall(TOOLBAR_RE, markup)), 1)
        self.assertEqual(len(re.findall(HEADER_RE, markup)), 1)

    def test_columns_appear_in_header(self):
        rendered = self.table.render("test_id")
        self.assertIn("Column 1", rendered)
        self.assertIn("Column 2", rendered)


class DeclarativeTableTestCase(TestCase):
    class Table(BootstrapTable):
        a = Column("Column 1")
        b = Column("Column 2", name='bar')

        def toolbar(self):
            yield "<span>"
            yield "Hasta la vista, baby!"
            yield "</span>"

    def test_columns_are_collected(self):
        Table = type(self).Table
        t = Table(data_url="")
        self.assertEqual(t.columns, [Table.a, Table.b])

    def test_column_names_are_undeferred(self):
        Table = type(self).Table
        self.assertEqual(Table.a.name, "a")
        self.assertEqual(Table.b.name, "bar")


class InheritanceTestCase(TestCase):
    def setUp(self):
        class A(BootstrapTable):
            a = Column("Foo")
            b = Column("Bar")

        class B(A):
            a = Column("Shizzle")
            c = Column("Baz")

        self.A = A
        self.B = B

    def test_inheritance_adds_columns_correctly(self):
        cols = self.B(data_url="#").columns
        self.assertEqual([(c.name, c.title) for c in cols],
                         [('a', "Shizzle"), ('b', "Bar"), ('c', "Baz")])

    def test_superclasses_columns_not_altered(self):
        self.assertEqual(self.A.column_attrname_map, {'a': 'a', 'b': 'b'})

    def test_table_args_defaults_set(self):
        class A(BootstrapTable):
            pass
        self.assertTrue(hasattr(A, '_table_args'),
                        "Attribute _table_args not set after class creation")

        self.assertEqual(dict(A._table_args), {'data-toggle': "table"})
        self.assertEqual(A("#").table_args,
                         {'data-toggle': "table", 'data-url': "#"})


class TableArgsTestCase(TestCase):
    def setUp(self):
        # we only use the metaclass so we don't have to test the defaults again
        class A(metaclass=BootstrapTableMeta):
            class Meta:
                table_args = {'arg1': "Bar", 'arg2': "Value"}

        class B(A):
            class Meta:
                table_args = {'arg2': "Antoher value", 'arg3': "x"}

        self.A = A
        self.B = B

    def test_table_args_inherited(self):
        self.assertTrue(hasattr(self.B, '_table_args'),
                        "Attribute _table_args not set after class creation")

        self.assertEqual(dict(self.B._table_args),
                         {'arg1': "Bar", 'arg2': "Antoher value", 'arg3': "x"})

    def test_table_args_of_superclass_untouched(self):
        self.assertEqual(dict(self.A._table_args), {'arg1': "Bar", 'arg2': "Value"})

    def test_meta_not_left_in_class(self):
        self.assertFalse(hasattr(self.A, 'Meta'))
        self.assertFalse(hasattr(self.B, 'Meta'))


class EnforcedUrlParamsTestCase(TestCase):
    def setUp(self):
        class A(BootstrapTable):
            class Meta:
                enforced_url_params = {'inverted': 'yes'}
        self.A = A

    def test_url_param_is_added(self):
        self.assertEqual(self.A("http://localhost/table").data_url,
                         "http://localhost/table?inverted=yes")

    def test_url_param_is_overridden(self):
        self.assertEqual(self.A("http://localhost/table?inverted=no").data_url,
                         "http://localhost/table?inverted=yes")


class SplittedTableTestCase(TestCase):
    def setUp(self):
        super().setUp()

        class Table(SplittedTable):
            splits = (('split1', "Split 1"), ('split2', "Split 2"))
            foo = Column("Foo")
            bar = Column("Bar")

        self.table = Table(data_url="#")

    def test_table_correct_cols(self):
        self.assertEqual([c.name for c in self.table.columns],
                         ['split1_foo', 'split1_bar', 'split2_foo', 'split2_bar'])

    def test_table_header_generation(self):
        items = list(self.table.generate_table_header())
        header = ''.join(items)

        GLOBAL_RE = r'<thead><tr>(.*)</tr><tr>(.*)</tr></thead>'
        match = re.fullmatch(GLOBAL_RE, header)
        self.assertIsNotNone(match)
        first_row, second_row = match.groups()

        BIG_COL_RE = r'<th.*?colspan="2".*?>\s*(.*?)\s*</th>'
        self.assertEqual(re.findall(BIG_COL_RE, first_row),
                         ["Split 1", "Split 2"])

        SMALL_COL_RE = r'<th (.*?)>\?*(.*?)\s*</th>'
        small_col_matches = re.findall(SMALL_COL_RE, second_row)
        # EXPECTED form of `small_col_matches`:
        # [(html_attr_string, 'Foo'), (…, 'Bar'), (…, 'Foo'), (…, # 'Bar')]
        # where 'data-url="splitX_colname"' in html_attr_string

        self.assertEqual([m[1] for m in small_col_matches],
                         ["Foo", "Bar", "Foo", "Bar"])

        # The data urls should have the correct prefixes
        expected_field_names = ["split1_foo", "split1_bar", "split2_foo", "split2_bar"]
        observed_attr_strings = (m[0] for m in small_col_matches)

        for expected_field_name, attr_string in zip(expected_field_names,
                                                    observed_attr_strings):
            DATA_FIELD_RE = r'data-field="(\w+)"'
            observed_field_name = re.search(DATA_FIELD_RE, attr_string).group(1)
            self.assertEqual(observed_field_name, expected_field_name)
