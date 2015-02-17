# coding=utf-8
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet
from tests.fixtures.dummy.dns_zones import DNSZoneData


class FinanceAccountData(DataSet):
    class registration_fee:
        name = u"Anmeldegebühren"
        type = "REVENUE"

    class semester_fee:
        name = u"Semesterbeiträge"
        type = "REVENUE"

    class late_fee:
        name = u"Versäumnisgebühren"
        type = "REVENUE"

    class additional_fee:
        name = u"Zusatzbeiträge"
        type = "REVENUE"


class PropertyGroupData(DataSet):
    class member:
        name = u"Mitglied"

    class network_access:
        name = u"Netzwerkanschluss"

    class away:
        name = u"Vorübergehend Ausgezogen"

    class violation:
        name = u"Verstoß"

    class moved_from_division:
        name = u"Umzug aus anderer Sektion"

    class already_paid_semester_fee:
        name = u"Beitrag bereits gezahlt"


class ConfigData(DataSet):
    class config:
        id = 1
        member_group = PropertyGroupData.member
        network_access_group = PropertyGroupData.network_access
        away_group = PropertyGroupData.away
        violation_group = PropertyGroupData.violation
        moved_from_division_group = PropertyGroupData.moved_from_division
        already_paid_semester_fee_group = PropertyGroupData.already_paid_semester_fee
        registration_fee_account = FinanceAccountData.registration_fee
        semester_fee_account = FinanceAccountData.semester_fee
        late_fee_account = FinanceAccountData.late_fee
        additional_fee_account = FinanceAccountData.additional_fee
        user_zone = DNSZoneData.users_agdsn_de


class PropertyData(DataSet):
    class network_access:
        property_group = PropertyGroupData.network_access
        name = "network_access"
        granted = True

    class registration_fee:
        property_group = PropertyGroupData.network_access
        name = "registration_fee"
        granted = True

    class semester_fee:
        property_group = PropertyGroupData.network_access
        name = "semester_fee"
        granted = True

    class late_fee:
        property_group = PropertyGroupData.member
        name = "late_fee"
        granted = True

    class moved_from_division:
        property_group = PropertyGroupData.moved_from_division
        name = "registation_fee"
        granted = False

    class already_paid:
        property_group = PropertyGroupData.already_paid_semester_fee
        name = "semester_fee"
        granted = False

    class away:
        property_group = PropertyGroupData.away
        name = "away"
        granted = True

    class violation:
        property_group = PropertyGroupData.violation
        name = "violation"
        granted = True

    class violation_network_access_deny:
        property_group = PropertyGroupData.violation
        name = "network_access"
        granted = False
