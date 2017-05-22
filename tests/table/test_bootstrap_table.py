from unittest import TestCase

from web.blueprints.helpers.table import Column, BootstrapTable

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
        t = BootstrapTable(columns=[], data_url="http://foobar")
        self.assertEqual(t.columns, [])
        self.assertEqual(t.data_url, "http://foobar")
        self.assertEqual(repr(t), "<BootstrapTable cols=0 data_url='http://foobar'>")
