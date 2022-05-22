import re

import pytest

from web.table.table import Column, BootstrapTable, SplittedTable, \
    BootstrapTableMeta, custom_formatter_column


class TestColumn:
    def test_init_requires_args(self):
        with pytest.raises(TypeError):
            Column()  # pylint: disable=no-value-for-parameter

    def test_instatiation_with_name_and_title_works(self):
        c = Column(title="Test Column", name="test_col")
        assert c.name == "test_col"
        assert c.title == "Test Column"
        assert c.width == 0
        assert c.cell_style == False
        assert repr(c) == "<Column 'test_col' title='Test Column'>"

    def test_instantiation_without_name(self):
        c = Column("Test Title")
        assert c.name is None
        assert c.title == "Test Title"

    def test_column_is_hidden(self):
        c = Column("Test", name='test_col', hide_if=lambda: True)
        assert str(c) == "", "Column rendered in spite of hide_if"

    def test_column_is_not_hidden(self):
        c = Column("Test", name='test_col', hide_if=lambda: False)
        assert str(c) != ""


class TestInstantiatedColumn:
    @pytest.fixture(scope='class')
    def column(self):
        return Column(title="Test Column", name="test_col")

    def test_col_args(self, column):
        arg_string = column.build_col_args()
        assert 'data-field="test_col"' in arg_string
        assert 'data-sortable="true"' in arg_string

    def test_col_render(self, column):
        rendered = str(column)
        assert column.render() == rendered
        assert rendered.startswith("<th")
        assert rendered.endswith("</th>")
        assert column.build_col_args() in rendered
        assert column.title in rendered


class TestCustomizedColumn:
    @pytest.fixture(scope='class')
    def rendered_col(self):
        return str(Column(title="Test Column", name="test_col",
                          width=3, cell_style="customCellStyle"))

    @pytest.mark.parametrize('arg_string', [
        'data-cell-style="customCellStyle"',
        'class="col-sm-3"',
    ])
    def test_custom_arguments_set(self, rendered_col, arg_string):
        assert arg_string in rendered_col


class TestBootstrapTable:
    def test_init_requires_args(self):
        with pytest.raises(TypeError):
            BootstrapTable()  # pylint: disable=no-value-for-parameter

    def test_minimal_instantiation(self):
        t = BootstrapTable(data_url="http://foobar")
        assert t.columns == []
        assert t.data_url == "http://foobar"
        assert repr(t) == "<BootstrapTable cols=0 data_url='http://foobar'>"


class TestInstantiatedBootstrapTable:
    @pytest.fixture(scope='class')
    def Table(self):
        class Table_(BootstrapTable):
            class Meta:
                table_args = {'foo': "bar", 'data-cache': "true"}
            col1 = Column("Column 1")
            col2 = Column("Column 2")
        return Table_

    @pytest.fixture(scope='class')
    def table(self, Table):
        return Table(data_url="http://dummy")

    @pytest.fixture(scope='class')
    def header(self, table):
        return str(table.table_header)

    def test_header_tags(self, header):
        assert header.startswith("<thead><tr>")
        assert header.endswith("</tr></thead>")

    def test_header_contains_col(self, table, header):
        for col in table.columns:
            assert str(col)
            assert str(col) in header

    def test_table_args_passed(self, table):
        assert table.table_args.get('data-cache') == "true"
        assert table.table_args.get('foo') == "bar"

    def test_table_args_parameter_take_precedence(self, Table):
        table = Table(data_url="#", table_args={'foo': "new"})
        assert table.table_args['foo'] == "new"

    def test_custom_table_args_will_be_used(self, table):
        table.table_args['special_arg'] = "someveryspecialargument"
        assert "someveryspecialargument" in table.render("some-id")

    @pytest.fixture(scope='class')
    def stub_table_render(self):
        class StubTable(BootstrapTable):
            def __init__(self):
                super().__init__(data_url="http://dummy")
            table_header = "HEADER"
            table_footer = "FOOTER"
            toolbar = "TOOLBAR"

        return StubTable().render(table_id="TABLE_ID")

    @pytest.mark.parametrize('pattern', [
        r'<div .*role="toolbar".*>\s*TOOLBAR\s*</div>',  # toolbar
        r'<table .*id="TABLE_ID".*>\s*HEADER\s*FOOTER\s*</table>',  # header
    ])
    def test_toolbar_render_contains_pattern_pattern(self, pattern, stub_table_render):
        assert len(re.findall(pattern, stub_table_render)) == 1

    @pytest.fixture(scope='class')
    def rendered(self, table):
        return table.render("test_id")

    @pytest.mark.parametrize('expected_needle', [
        "Column 1", "Column 2",
    ])
    def test_columns_appear_in_header(self, rendered, expected_needle):
        assert expected_needle in rendered


class TestDeclarativeTable:
    @pytest.fixture(scope='class')
    def table_cls(self):
        class Table(BootstrapTable):
            a = Column("Column 1")
            b = Column("Column 2", name='bar')

            def toolbar(self):
                yield "<span>"
                yield "Hasta la vista, baby!"
                yield "</span>"
        return Table

    def test_columns_are_collected(self, table_cls):
        t = table_cls(data_url="")
        assert t.columns == [table_cls.a, table_cls.b]

    def test_column_names_are_undeferred(self, table_cls):
        assert table_cls.a.name == "a"
        assert table_cls.b.name == "bar"


class TestInheritance:
    @pytest.fixture(scope='class')
    def A(self):
        class A_(BootstrapTable):
            a = Column("Foo")
            b = Column("Bar")
        return A_

    @pytest.fixture(scope='class')
    def B(self, A):
        class B_(A):
            a = Column("Shizzle")
            c = Column("Baz")
        return B_

    def test_inheritance_adds_columns_correctly(self, B):
        cols = B(data_url="#").columns
        assert [(c.name, c.title) for c in cols] == [('a', "Shizzle"), ('b', "Bar"), ('c', "Baz")]

    def test_superclasses_columns_not_altered(self, A):
        assert A.column_attrname_map == {'a': 'a', 'b': 'b'}

class TestEmptyTableDefaults:
    @pytest.fixture(scope='class')
    def EmptyTable(self) -> type[BootstrapTable]:
        class A(BootstrapTable):
            pass
        return A

    def test_table_args_set(self, EmptyTable):
        assert hasattr(EmptyTable, '_table_args'), "Attribute _table_args not set after class creation"
        assert dict(EmptyTable._table_args) == {
            'data-toggle': "table",
            "data-icons-prefix": "fa",
        }

    def test_table_args_after_instantiation(self, EmptyTable):
        assert EmptyTable("#").table_args == {
            'data-toggle': "table",
            "data-icons-prefix": "fa",
            'data-url': "#",
        }


class TestTableArgs:
    @pytest.fixture(scope='class')
    def A(self):
        # we only use the metaclass so we don't have to test the defaults again
        class A_(metaclass=BootstrapTableMeta):
            class Meta:
                table_args = {'arg1': "Bar", 'arg2': "Value"}
        return A_

    @pytest.fixture(scope='class')
    def B(self, A):
        class B_(A):
            class Meta:
                table_args = {'arg2': "Antoher value", 'arg3': "x"}

        return B_

    def test_table_args_inherited(self, A, B):
        assert hasattr(B, '_table_args'), "Attribute _table_args not set after class creation"
        assert dict(B._table_args) == {'arg1': "Bar", 'arg2': "Antoher value", 'arg3': "x"}

    def test_table_args_of_superclass_untouched(self, A):
        assert dict(A._table_args) == {'arg1': "Bar", 'arg2': "Value"}

    def test_meta_not_left_in_class(self, A, B):
        assert not hasattr(A, 'Meta')
        assert not hasattr(B, 'Meta')


class TestEnforcedUrlParams:
    @pytest.fixture(scope='class')
    def A(self):
        class A_(BootstrapTable):
            class Meta:
                enforced_url_params = {'inverted': 'yes'}
        return A_

    def test_url_param_is_added(self, A: type[BootstrapTable]):
        assert A("http://localhost/table").data_url == "http://localhost/table?inverted=yes"

    def test_url_param_is_overridden(self, A: type[BootstrapTable]):
        assert A("http://localhost/table?inverted=no").data_url == "http://localhost/table?inverted=yes"


class TestSplittedTable:
    @pytest.fixture(scope='class')
    def table(self):
        class Table(SplittedTable):
            splits = (('split1', "Split 1"), ('split2', "Split 2"))
            foo = Column("Foo")
            bar = Column("Bar")

        return Table(data_url="#")

    def test_table_correct_cols(self, table):
        assert [c.name for c in table.columns] \
            == ['split1_foo', 'split1_bar', 'split2_foo', 'split2_bar']

    @pytest.fixture(scope='class')
    def header(self, table):
        return str(table.table_header)

    def test_table_header_generation(self, header):
        GLOBAL_RE = r'<thead><tr>(.*)</tr><tr>(.*)</tr></thead>'
        match = re.fullmatch(GLOBAL_RE, header)
        assert match is not None
        first_row, second_row = match.groups()

        BIG_COL_RE = r'<th.*?colspan="2".*?>\s*(.*?)\s*</th>'
        assert re.findall(BIG_COL_RE, first_row) == ["Split 1", "Split 2"]

        SMALL_COL_RE = r'<th (.*?)>\?*(.*?)\s*</th>'
        small_col_matches = re.findall(SMALL_COL_RE, second_row)
        # EXPECTED form of `small_col_matches`:
        # [(html_attr_string, 'Foo'), (…, 'Bar'), (…, 'Foo'), (…, # 'Bar')]
        # where 'data-url="splitX_colname"' in html_attr_string

        assert [m[1] for m in small_col_matches] == ["Foo", "Bar", "Foo", "Bar"]

        # The data urls should have the correct prefixes
        expected_field_names = ["split1_foo", "split1_bar", "split2_foo", "split2_bar"]
        observed_attr_strings = (m[0] for m in small_col_matches)

        for expected_field_name, attr_string in zip(expected_field_names, observed_attr_strings):
            DATA_FIELD_RE = r'data-field="(\w+)"'
            observed_field_name = re.search(DATA_FIELD_RE, attr_string).group(1)
            assert observed_field_name == expected_field_name


class TestFormattedColumn:
    def test_column_formatter_passed(self):
        @custom_formatter_column('table.myFormatter')
        class MyCol(Column):
            pass
        assert MyCol("Title!").formatter == 'table.myFormatter', "Formatter not passed by decorator"

    def test_column_formatter_respects_init(self):
        @custom_formatter_column('table.myFormatter')
        class MyCol(Column):
            def __init__(self, *a, **kw):
                super().__init__(*a, sortable=False, **kw)
        assert not MyCol("Title!").sortable
