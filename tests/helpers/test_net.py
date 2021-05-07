import pytest

from pycroft.helpers import net


@pytest.mark.parametrize('value', ['141.30.228.39'])
def test_good_ips(value: str):
    assert net.ip_regex.match(value)


@pytest.mark.parametrize('value', [
    "141.3330.228.39", "141.3330.228.39.", "ddddddd"
])
def test_bad_ips(value: str):
    assert not net.ip_regex.match(value)
