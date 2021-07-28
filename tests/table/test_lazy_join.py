import pytest

from web.table.table import lazy_join


def test_simple_join():
    @lazy_join
    def foo():
        yield "one"
        yield "two"
        yield "three"
    assert str(foo()) == "onetwothree"

def test_join_with_spaces():
    @lazy_join(" ")
    def foo():
        yield "one"
        yield "two"
        yield "three"

    assert str(foo()) == "one two three"

def test_elements_are_cast_to_string():
    @lazy_join
    def foo():
        yield "a"
        yield 3
        yield False
        yield None

    assert str(foo()) == "a3False"
    assert list(foo()) == ["a", "3", "False", ""]

def test_glue_is_added_in_iterator():
    @lazy_join("\n")
    def foo():
        yield "one"
        yield "two"
        yield "three"

    assert list(foo()) == ["one", "\n", "two", "\n", "three"]

def test_nested_usage():
    @lazy_join(", ")
    def inner():
        yield "a"
        yield "b"

    @lazy_join("\n")
    def outer():
        yield "<span>"
        yield inner()
        yield "</span>"

    assert str(outer()) == "<span>\na, b\n</span>"


@pytest.fixture(scope='module')
def foo_joined():
    @lazy_join
    def foo():
        yield "a"
        yield "b"

    return foo


@pytest.mark.parametrize('call1', [str, list])
@pytest.mark.parametrize('call2', [str, list])
def test_exhaustion(foo_joined, call1, call2):
    gen = foo_joined()
    call1(gen)
    with pytest.raises(RuntimeError):
        call2(gen)
