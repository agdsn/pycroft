import pytest

from hades_logs.parsing import parse_vlan as parse, ParsingError


def test_correct_untagged():
    assert parse('"2hades-unauth"') == "hades-unauth (untagged)"


def test_correct_untagged_unstriped():
    assert parse("2Wu5") == "Wu5 (untagged)"


def test_correct_tagged():
    assert parse("1toothstone") == "toothstone (tagged)"


def test_bad_taggedness_raises_parsingerror():
    with pytest.raises(ParsingError):
        parse('"3some-vlan"')


def test_empty_name_raises_parsingerror():
    with pytest.raises(ParsingError):
        parse('"2"')
