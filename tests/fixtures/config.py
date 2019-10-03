# coding=utf-8
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet

from .dummy import finance, address

class AccountData(DataSet):
    class membership_fee:
        name = u"Mitgliedsbeiträge"
        type = "REVENUE"


class PropertyGroupData(DataSet):
    class member:
        name = u"Mitglied"

    class network_access:
        name = u"Netzwerkanschluss"

    class away:
        # Although there is no `away` group known to the pycroft model
        # anymore, it is needed to test the `reduced_membership_fee`
        # logic.  The whole thing is to be removed in the future,
        # anyway.  See #28 on github.
        name = u"Ausgezogen, Mail"

    class violation:
        name = u"Verstoß"

    class cache:
        name = "Cache"

    class traffic_limit_exceeded:
        name = u"Trafficlimit überschritten"

    class payment_in_default:
        name = u"Zahlungsrückstand"

    class external:
        name = u"Extern"

    class caretaker:
        name = "Hausmeister"

    class blocked:
        name = "Gesperrt"

    class treasurer:
        name = "Finanzer"


class ConfigData(DataSet):
    class config:
        id = 1
        member_group = PropertyGroupData.member
        network_access_group = PropertyGroupData.network_access
        violation_group = PropertyGroupData.violation
        cache_group = PropertyGroupData.cache
        traffic_limit_exceeded_group = PropertyGroupData.traffic_limit_exceeded
        payment_in_default_group = PropertyGroupData.payment_in_default
        external_group = PropertyGroupData.external
        blocked_group = PropertyGroupData.blocked
        caretaker_group = PropertyGroupData.caretaker
        treasurer_group = PropertyGroupData.treasurer
        membership_fee_account = AccountData.membership_fee
        membership_fee_bank_account = finance.BankAccountData.dummy
        dummy_address = address.AddressData.dummy_address

class PropertyData(DataSet):
    class network_access:
        property_group = PropertyGroupData.member
        name = "network_access"
        granted = True

    class membership_fee:
        property_group = PropertyGroupData.member
        name = "membership_fee"
        granted = True

    class away:
        property_group = PropertyGroupData.away
        name = "reduced_membership_fee"
        granted = True

    class violation:
        property_group = PropertyGroupData.violation
        name = "violation"
        granted = True

    class violation_network_access_deny:
        property_group = PropertyGroupData.violation
        name = "network_access"
        granted = False

    class cache:
        property_group = PropertyGroupData.cache
        name = "cache_access"
        granted = False

    class traffic_limit_exceeded:
        property_group = PropertyGroupData.traffic_limit_exceeded
        granted = True
        name = "traffic_limit_exceeded"

    class payment_in_default:
        property_group = PropertyGroupData.payment_in_default
        name = "payment_in_default"
        granted = True

    class member:
        property_group = PropertyGroupData.member
        name = "member"
        granted = True
