# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from collections import OrderedDict


property_categories = OrderedDict((
    ("Mitglieder", OrderedDict((
        ('member', "ist Mitglied"),
        ("network_access",  "besitzt Zugang zum Studentennetz"),
        ("membership_fee",  "ist verpflichtet den Mitgliedsbeitrag zu bezahlen"),
        ("violation",  "hat gegen Regeln verstoßen"),
    ))),
    ("System / Dienste", OrderedDict((
        ('ldap', "hat einen Directory-Eintrag im LDAP"),
        ('ldap_login_enabled', "hat einen aktivierten Directory-Eintrag im LDAP"),
        ('mail', "hat Zugriff auf Mailkonto"),
        ('userdb', "kann sich eine MySQL-Datenbank erstellen"),
        ('userwww', "hat Zugriff auf das Userhosting"),
        ('cache_access', "verwendet den Cache"),
        ('traffic_limit_exceeded', "hat Traffic-Limit überschritten"),
        ('sipa_login', "kann sich bei SIPA anmelden"),
    ))),
    ("Nutzerverwaltung", OrderedDict((
        ("user_show",  "darf Nutzerdaten einsehen"),
        ("user_change",  "darf Nutzer anlegen, ändern, löschen"),
        ("user_hosts_change",  "darf Hosts & Interfaces ändern"),
    ))),
    ("Finanzen", OrderedDict((
        ("finance_show",  "darf Finanzendaten einsehen"),
        ("finance_change",  "darf Finanzendaten ändern"),
        ("payment_in_default",  "im Zahlungsrückstand"),
    ))),
    ("Infrastruktur", OrderedDict((
        ("infrastructure_show",  "darf Infrastruktur ansehen"),
        ("infrastructure_change",  "darf Infrastruktur anlegen, bearbeiten, löschen"),
        ("facilities_show",  "darf Gebäude einsehen"),
        ("facilities_change",  "darf Gebäude anlegen, bearbeiten, löschen"),
    ))),
    ("Gruppenverwaltung", OrderedDict((
        ("groups_show",  "darf Gruppen einsehen"),
        ("groups_change_membership",  "darf Gruppenmitgliedschaften bearbeiten"),
        ("groups_change",  "darf Gruppen anlegen, bearbeiten, löschen"),
    ))),
))
