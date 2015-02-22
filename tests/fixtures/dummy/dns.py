# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet

from tests.fixtures.dummy.host import IpData, UserHostData


class ARecordData(DataSet):
    class without_ttl:
        address = IpData.dummy_user_ipv4
        name = "www.dummy.de."
        host = UserHostData.dummy_host1

    class with_ttl(without_ttl):
        time_to_live = 1000


class AAAARecordData(DataSet):
    class without_ttl:
        address = IpData.dummy_user_ipv6
        name = "www.dummy.de."
        host = UserHostData.dummy_host1

    class with_ttl(without_ttl):
        time_to_live = 1000


class MXRecordData(DataSet):
    class dummy:
        domain = "dummy.de."
        server = "mail.dummy.de."
        priority = 10
        host = UserHostData.dummy_host1


class CNAMERecordData(DataSet):
    class for_a:
        name = "dummy.net."
        record_for = ARecordData.without_ttl
        host = UserHostData.dummy_host1

    class for_aaaa:
        name = "dummy2.net."
        record_for = AAAARecordData.without_ttl
        host = UserHostData.dummy_host1


class NSRecordData(DataSet):
    class without_ttl:
        server = "server.dummy.de."
        domain = "dummy.de."
        host = UserHostData.dummy_host1

    class with_ttl(without_ttl):
        time_to_live = 1000


class SRVRecordData(DataSet):
    class without_ttl:
        service = "_xmpp._tcp.dummy.de."
        priority = 10
        weight = 50
        port = 5050
        target = "xmpp.dummy.de."
        host = UserHostData.dummy_host1

    class with_ttl(without_ttl):
        time_to_live = 1000
