import unittest

from pycroft.helpers import net


class IpRegexTestCase(unittest.TestCase):
    def test_ip_regex(self):
        regex = net.ip_regex
        self.assertTrue(regex.match("141.30.228.39"))
        self.assertFalse(regex.match("141.3330.228.39"))
        self.assertFalse(regex.match("141.3330.228.39."))
        self.assertFalse(regex.match("ddddddd"))
