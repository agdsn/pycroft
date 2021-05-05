from unittest import TestCase

from hades_logs import RadiusLogEntry


class EntryRejectionTestCase(TestCase):
    def assert_acceptance_from_reply(self, reply, should_accept=False):
        entry = RadiusLogEntry(mac=None, reply=reply, groups=None,
                               raw_attributes=None, timestamp=None)
        if should_accept:
            self.assertTrue(entry.accepted)
            self.assertTrue(entry)
        else:
            self.assertFalse(entry.accepted)
            self.assertFalse(entry)

    def test_explicit_reject(self):
        self.assert_acceptance_from_reply("Access-Reject")

    def test_implicit_reject(self):
        self.assert_acceptance_from_reply("SomeBogusValue")

    def test_accept(self):
        self.assert_acceptance_from_reply("Access-Accept", should_accept=True)
