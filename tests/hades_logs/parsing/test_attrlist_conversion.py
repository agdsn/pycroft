from unittest import TestCase

from hades_logs.parsing import attrlist_to_dict


class AttrListConversionTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.to_dict = attrlist_to_dict

    def test_assert_unhashable_key_raises_typeerror(self):
        with self.assertRaises(TypeError):
            self.to_dict([(["listsarebadaskeys"], "valuedoesntmatter")])

    def test_all_values_parsed_correctly(self):
        dict_gotten = self.to_dict([
            ('Egress-VLAN-Name', "2hades-unauth"),
            ('Egress-VLAN-Name', "1toothstone"),
            ('Egress-VLAN-Name2', "2Wu5"),
            ('Other-Attribute', '')
        ])
        self.assertEqual(dict_gotten, {
            'Egress-VLAN-Name': ["2hades-unauth", "1toothstone"],
            'Egress-VLAN-Name2': ["2Wu5"],
            'Other-Attribute': [''],
        })
