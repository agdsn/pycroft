import re
from unittest import TestCase

from web.blueprints.helpers.table import Column, BootstrapTable, SplittedTable

class ColumnTestCase(TestCase):
    def test_init_requires_args(self):
        with self.assertRaises(TypeError):
            Column()  # pylint: disable=no-value-for-parameter

    def test_instatiation_with_name_and_title_works(self):
        c = Column(name="test_col", title="Test Column")
        self.assertEqual(c.name, "test_col")
        self.assertEqual(c.title, "Test Column")
        self.assertEqual(c.width, 0)
        self.assertEqual(c.cell_style, False)
        self.assertEqual(repr(c), "<Column 'test_col' title='Test Column'>")

class InstantiatedColumnTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.column = Column(name="test_col", title="Test Column")

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
        rendered = str(Column(name="test_col", title="Test Column",
                              width=3, cell_style="customCellStyle"))
        self.assertIn('data-cell-style="customCellStyle"', rendered)
        self.assertIn('class="col-sm-3"', rendered)


class BootstrapTableTestCase(TestCase):
    def test_init_requires_args(self):
        with self.assertRaises(TypeError):
            BootstrapTable()  # pylint: disable=no-value-for-parameter


    def test_minimal_instantiation(self):
        t = BootstrapTable(columns=["dummy"], data_url="http://foobar")
        self.assertEqual(t.columns, ["dummy"])
        self.assertEqual(t.data_url, "http://foobar")
        self.assertEqual(repr(t), "<BootstrapTable cols=1 data_url='http://foobar'>")


class InstantiatedBootstrapTableTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.table = BootstrapTable(
            columns=[Column(name="col1", title="Column 1"),
                     Column(name="col2", title="Column 2")],
            data_url="http://dummy",
            table_args={'foo': "bar", 'data-cache': "true"}
        )

    def test_table_header_generation(self):
        elements = list(self.table.generate_table_header())
        header = ''.join(elements)
        self.assertTrue(header.startswith("<thead><tr>"))
        self.assertTrue(header.endswith("</tr></thead>"))
        for col in self.table.columns:
            self.assertTrue(str(col))
            self.assertIn(str(col), elements)

    def test_table_args_passed(self):
        self.assertEqual(self.table.table_args.get('data-cache'), "true")
        self.assertEqual(self.table.table_args.get('foo'), "bar")

    def test_render_uses_the_generators_correctly(self):
        class MockedTable(BootstrapTable):
            def __init__(self):
                super().__init__(columns=[], data_url="http://dummy")
            generate_table_header = lambda self: ["HEADER"]
            generate_table_footer = lambda self: ["FOOTER"]
            generate_toolbar = lambda self: ["TOOLBAR"]

        markup = MockedTable().render(table_id="TABLE_ID")
        TOOLBAR_RE = r'<div .*role="toolbar".*>\s*TOOLBAR\s*</div>'
        HEADER_RE = r'<table .*id="TABLE_ID".*>\s*HEADER\s*FOOTER\s*</table>'

        self.assertEqual(len(re.findall(TOOLBAR_RE, markup)), 1)
        self.assertEqual(len(re.findall(HEADER_RE, markup)), 1)


class SplittedTableTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.table = SplittedTable(
            splits=(('split1', "Split 1"), ('split2', "Split 2")),
            columns=[Column('foo', "Foo"), Column('bar', "Bar")],
            data_url="#"
        )

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
