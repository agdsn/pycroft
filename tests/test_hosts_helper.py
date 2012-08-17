from tests import OldPythonTestCase
from random import randint
from pycroft.helpers.host_helper import sort_ports, generate_hostname

class Test_010_SimpleHostsHelper(OldPythonTestCase):
    def test_0010_sort_ports(self):
        ports = []
        for letter in ["A", "B", "C", "D", "E", "F", "G"]:
            for number in range(1, 24):
                ports.append("%s%d" % (letter, number))

        class fake_port(object):
            def __init__(self, name):
                self.name = name

        pool = list(ports)
        shuffled = []
        for selected in range(0, len(ports)):
            idx = randint(0, len(pool) - 1)
            shuffled.append(fake_port(pool[idx]))
            del pool[idx]
        resorted = [p.name for p in sort_ports(shuffled)]
        self.assertEqual(resorted, ports)

    def test_0020_generate_hostname(self):
        networks = ["141.30.228", "10.10.10", "141.30.126"]
        for hostpart in range(1, 255):
            for net in networks:
                expected = "whdd%d" % hostpart
                generated = generate_hostname("%s.%d" % (net, hostpart))
                self.assertEqual(generated, expected)