# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from tests import OldPythonTestCase
from random import randint
from pycroft.helpers.host_helper import sort_ports

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
