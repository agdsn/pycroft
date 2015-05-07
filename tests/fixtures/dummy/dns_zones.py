# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet


class DNSZoneData(DataSet):
    class users_agdsn_de:
        name = "users.agdsn.de"

    class example_com:
        name = "example.com"

    class reverse_192_168_0:
        name = "0.168.192.in-addr.arpa"

    class reverse_192_168_1:
        name = "1.168.192.in-addr.arpa"

    class reverse_2001_cdba_0000:
        name = "4.3.2.1.8.b.d.0.1.0.0.2.ip6.arpa"
