from functools import reduce
# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
member_props = {"member": True,
                "network_access": True,
                "membership_fee": True,
                "ldap": True,
                "mail": True,
                "userdb": True,
                "userwww": True}

org_props = {"user_show": True,
             "user_change": True,
             "user_mac_change": True,
             "finance_show": True,
             "infrastructure_show": True,
             "facilities_show": True,
             "groups_show": True,
             "groups_change_membership": True,
             "groups_traffic_show": True}

finance_admin_props = {"finance_change": True}

group_admin_props = {"groups_show": True,
                     "groups_change_membership": True,
                     "groups_change": True,
                     "groups_traffic_show": True,
                     "groups_traffic_change": True}

infra_admin_props = {"infrastructure_show": True,
                     "infrastructure_change": True,
                     "facilities_show": True,
                     "facilities_change": True}


group_props = {
    "caretaker": ("Hausmeister", {"network_access": True}),

    "external": ("Extern", {'network_access': True}),

    "member": ("Mitglied", member_props),

    "org": ("Org", org_props),

    "finance_admin": ("Finanzer", finance_admin_props),

    "suspended": ("Gesperrt", {"network_access": False}),

    "finance": ("Zahlungsrückstand", {"network_access": False, "payment_in_default": True}),
    "traffic": ("Trafficüberschreitung", {"network_access": False, "traffic_limit_exceeded": True}),
    "violator": ("Verstoß gegen Netzordnung", {"network_access": False,
                                              "violation": True}),

    "cache_user": ("Cache Nutzer", {"cache_access": True}),

    # nutzer ∈ member \ away = normales mitglied, mailmitgliedschaft, semesterbeitrag
    #        ∈ away ∩ member = temporär ausgezogen, mailmitgliedschaft, reduzierter semesterbeitrag
    #        ∈ away \ member = permanent ausgezogen, mailmitgliedschaft, reduzierter semesterbeitrag
    #        ∉ away ∪ member = permanent ausgezogen, keine mailmitgliedschaft, kein semesterbeitrag
    "away": ("Ausgezogen (obsolet, ehem. „mail“)", {"network_access": False,
                                                    "membership_fee": False,
                                                    "mail": True,
                                                    'ldap': True,
                                                    'userdb': True,
                                                    'userwww': True}),

    "root": ("Root", reduce(lambda d1,d2: dict(d1, **d2), [org_props,
                                                           finance_admin_props,
                                                           group_admin_props,
                                                           infra_admin_props,
                                                           {'mail': True,
                                                            'ldap': True,
                                                            'userdb': True,
                                                            'userwww': True}
                                                           ]))
}


# Memberships being added due to the current status
status_groups_map = {
    # `usertraffic` is a traffic group, so not given in `import_conf`
    1: ("member", "usertraffic"),  # bezahlt, ok
    2: ("member", "finance", "usertraffic"),  # angemeldet, aber nicht bezahlt
    3: ("finance",),    # nicht bezahlt, hat nur Mail
    4: ("member", "finance", "usertraffic"),  # angemeldet, nicht bezahlt, 2. Warnung
    5: ("member", "suspended", "usertraffic"),  # angemeldet, nicht bezahlt, gesperrt
    6: ("away",),  # angemeldet, gesperrt (ruhend)
    7: ("member", "violator", "usertraffic"),  # angemeldet, gesperrt (Verstoss gegen Netzordnung)
    8: (),  # ausgezogen, gesperrt
    9: (),  # Ex-Aktiver
    10: ("away",), # E-Mail, ehemals IP
    11: (),  # uebrig in Wu die in Renovierung
    12: ("member", "traffic", "usertraffic")  # gesperrt wegen Trafficueberschreitung
}


site_name_map = {
    0: u"Wundtstraße/Zellescher Weg",
    1: u"Borsbergstraße",
    2: u"Zeunerstraße",
    3: u"Budapester Straße",
    4: "Fritz-Löffler-Straße",
    5: "Gret-Palucca-Straße",
    6: "Neuberinstraße",
    7: "Wachwitzer Bergstraße",
    8: "August-Bebel-Straße",
}


building_site_map = {
    # building_id: site_id
    1: 0,  # Wu5
    2: 0,  # Wu7
    3: 0,  # Wu9
    4: 0,  # Wu11
    5: 0,  # Wu1
    6: 0,  # Wu3
    7: 0,  # ZW41
    8: 0,  # ZW41A
    9: 0,  # ZW41B
    10: 0,  # ZW41C
    11: 0,  # ZW41D
    12: 1,  # Bor34
    13: 2,  # Zeu1f
    14: 3,  # Bu22
    15: 3,  # Bu24
    16: 4,  # FL16
    17: 5,  # GPS11
    18: 6,  # Neu15
    19: 7,  # WBS21
    20: 8,  # Tus
}

building_subnets_map = {
    # building_id: subnet_id
    1: [6],  # Wu5
    2: [3],  # Wu7
    3: [8],  # Wu9
    4: [7],  # Wu11
    5: [1],  # Wu1
    6: [2],  # Wu3
    7: [4],  # ZW41
    8: [4],  # ZW41A
    9: [4],  # ZW41B
    10: [4],  # ZW41C
    11: [4],  # ZW41D
    12: [10],  # Bor34
    13: [11],  # Zeu1f
    14: [13],  # Bu22
    15: [14],  # Bu24
    16: [15],  # FL16
    17: [16],  # GPS11
    18: [17],  # Neu15
    19: [18],  # WBS21
    20: [19],  # WBS21
}

vlan_name_vid_map = {
    # Vlan_name: VLAN ID (on the switches)
    'Wu1': 11,
    'Wu3': 13,
    'Wu5': 15,
    'Wu7': 17,
    'Wu9': 19,
    'Wu11': 5,
    'ZW41': 41,
    'Bor34': 34,
    'Servernetz': 22,
    'UNEP': 348,
    'Zeu1f': 234,
    'Bu22': 18,
    'Bu24': 29,
    'FL16': 35,
    'GPS11': 32,
    'Neu15': 666,  # WARNING: BOGUS VALUE
    'WBS21': 667,
    'Tus': 667,
}
