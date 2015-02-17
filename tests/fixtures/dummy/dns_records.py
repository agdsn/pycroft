# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet

from tests.fixtures.dummy.dns_zones import DNSZoneData
from tests.fixtures.dummy.host import IPData


class DNSNameData(DataSet):
    class example_com:
        name = "@"
        zone = DNSZoneData.example_com

    class www_example_com:
        name = "www"
        zone = DNSZoneData.example_com

    class mail_example_com:
        name = "mail"
        zone = DNSZoneData.example_com

    class smtp_example_com:
        name = "smtp"
        zone = DNSZoneData.example_com

    class srv_xmpp_example_com:
        name = "_xmpp._tcp"
        zone = DNSZoneData.example_com

    class chat_example_com:
        name = "chat"
        zone = DNSZoneData.example_com

    class subdomain_example_com:
        name = "subdomain"
        zone = DNSZoneData.example_com

    class ns_example_com:
        name = "ns"
        zone = DNSZoneData.example_com


class AddressRecordData(DataSet):
    class ipv4:
        name = DNSNameData.www_example_com
        address = IPData.dummy_user_ipv4

    class ipv6:
        name = DNSNameData.www_example_com
        address = IPData.dummy_user_ipv6


class MXRecordData(DataSet):
    class dummy:
        name = DNSNameData.example_com
        preference = 10
        exchange = DNSNameData.mail_example_com


class CNAMERecordData(DataSet):
    class dummy:
        name = DNSNameData.smtp_example_com
        cname = DNSNameData.mail_example_com


class NSRecordData(DataSet):
    class dummy:
        name = DNSNameData.subdomain_example_com
        nsdname = DNSNameData.ns_example_com


class SOARecordData(DataSet):
    class dummy:
        name = DNSNameData.example_com
        mname = DNSNameData.ns_example_com
        rname = "nsadmin@example.com"
        serial = 2010102301
        refresh = 86400
        retry = 7200
        expire = 3600000
        minimum = 172800


class SRVRecordData(DataSet):
    class dummy:
        name = DNSNameData.srv_xmpp_example_com
        priority = 10
        weight = 50
        port = 5050
        target = DNSNameData.chat_example_com


class TXTRecordData(DataSet):
    class dummy:
        name = DNSNameData.example_com
        txt_data = "Test"
