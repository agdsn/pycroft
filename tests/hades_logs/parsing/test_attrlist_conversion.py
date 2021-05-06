import pytest

from hades_logs.parsing import attrlist_to_dict


def test_assert_unhashable_key_raises_typeerror():
    with pytest.raises(TypeError):
        attrlist_to_dict([(["listsarebadaskeys"], "valuedoesntmatter")])


def test_all_values_parsed_correctly():
    dict_gotten = attrlist_to_dict([
        ('Egress-VLAN-Name', "2hades-unauth"),
        ('Egress-VLAN-Name', "1toothstone"),
        ('Egress-VLAN-Name2', "2Wu5"),
        ('Other-Attribute', '')
    ])
    assert dict_gotten == {
        'Egress-VLAN-Name': ["2hades-unauth", "1toothstone"],
        'Egress-VLAN-Name2': ["2Wu5"],
        'Other-Attribute': [''],
    }
