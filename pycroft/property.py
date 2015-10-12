# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from collections import OrderedDict


property_categories = OrderedDict((
    (u"Mitglieder", OrderedDict((
        (u"network_access",  u"besitzt Zugang zum Studentennetz"),
        (u"mail", u"hat Zugriff auf Mailkonto"),
        (u"registration_fee",  u"ist verpflichtet Anmeldegebühr zu bezahlen"),
        (u"semester_fee",  u"ist verpflichtet Semesterbeitrag zu bezahlen"),
        (u"reduced_semester_fee", u"muss nur reduzierten Semesterbeitrag bezahlen"),
        (u"late_fee",  u"ist verpflichtet Versäumnisgebühr zu bezahlen"),
    ))),
    (u"Nutzerverwaltung", OrderedDict((
        (u"user_show",  u"darf Nutzerdaten einsehen"),
        (u"user_change",  u"darf Nutzer anlegen, ändern, löschen"),
        (u"user_mac_change",  u"darf MAC-Adressen ändern"),
    ))),
    (u"Finanzen", OrderedDict((
        (u"finance_show",  u"darf Finanzendaten einsehen"),
        (u"finance_change",  u"darf Finanzendaten ändern"),
    ))),
    (u"Infrastruktur", OrderedDict((
        (u"infrastructure_show",  u"darf Infrastruktur ansehen"),
        (u"infrastructure_change",  u"darf Infrastruktur anlegen, bearbeiten, löschen"),
        (u"facilities_show",  u"darf Gebäude einsehen"),
        (u"facilities_change",  u"darf Gebäude anlegen, bearbeiten, löschen"),
    ))),
    (u"Gruppenverwaltung", OrderedDict((
        (u"groups_show",  u"darf Gruppen einsehen"),
        (u"groups_change_membership",  u"darf Gruppenmitgliedschaften bearbeiten"),
        (u"groups_change",  u"darf Gruppen anlegen, bearbeiten, löschen"),
        (u"groups_traffic_show",  u"darf Trafficgruppen sehen"),
        (u"groups_traffic_change",  u"darf Trafficgruppen bearbeiten"),
    ))),
))
