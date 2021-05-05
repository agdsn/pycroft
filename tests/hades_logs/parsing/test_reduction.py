from unittest import TestCase

from hades_logs import RadiusLogEntry
from hades_logs.parsing import reduce_to_first_occurrence


class ReductionTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.func = reduce_to_first_occurrence
        self.elements = [0, 2, 1, 1, 1, 3, 4, 1, 1, 3, 3, 5, 5, 5, 0, 0]


    def test_simple_reduction(self):
        self.assertEqual(list(self.func(self.elements)),
                         [0, 2, 1, 3, 4, 1, 3, 5, 0])

    def test_nontrivial_equivalence_gives_first_representative(self):
        def _eq(a, b):
            """Return whether a and b are equivalent modulo 2"""
            return (a - b) % 2 == 0

        self.assertEqual(list(self.func(self.elements, comparator=_eq)),
                         [0, 1, 4, 1, 0])

    def test_radius_logs_work_as_well(self):
        timestamp = 1501623826.391414
        entries = [RadiusLogEntry(*e) for e in [
            ('00:de:ad:be:ef:00',
             'Access-Accept',
             ['traffic'],
             [['Egress-VLAN-Name', '"2hades-unauth"']],
             timestamp),
            ('00:de:ad:be:ef:00',
             'Access-Accept',
             ['traffic'],
             [['Egress-VLAN-Name', '"2hades-unauth"']],
             timestamp - 50),
            ('00:de:ad:be:ef:00',
             'Access-Accept',
             ['violation'],
             [['Egress-VLAN-Name', '"2hades-unauth"']],
             timestamp - 100),
        ]]
        reduced = list(self.func(entries, comparator=RadiusLogEntry.effectively_equal))
        self.assertEqual(len(reduced), 2)
        self.assertEqual(reduced[0], entries[0])
        self.assertEqual(reduced[-1], entries[-1])
