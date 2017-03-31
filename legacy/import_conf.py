# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
member_props = {"network_access": True,
                "semester_fee": True,
                "late_fee": True,
                "registration_fee": True,
                "mail": True}

org_props = {"user_show": True,
             "user_change": True,
             "user_mac_change": True,
             "finance_show": True,
             "infrastructure_show": True,
             "facilities_show": True,
             "groups_show": True,
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

    "member": ("Mitglied", member_props),

    "org": ("Org", org_props),

    "finance_admin": ("Finanzer", finance_admin_props),

    "suspended": ("Gesperrt", {"network_access": False}),

    "violator": ("Verstoß gegen Netzordnung", {"network_access": False,
                                              "violation": True}),

    # nutzer ∈ member \ away = normales mitglied, mailmitgliedschaft, semesterbeitrag
    #        ∈ away ∩ member = temporär ausgezogen, mailmitgliedschaft, reduzierter semesterbeitrag
    #        ∈ away \ member = permanent ausgezogen, mailmitgliedschaft, reduzierter semesterbeitrag
    #        ∉ away ∪ member = permanent ausgezogen, keine mailmitgliedschaft, kein semesterbeitrag
    "away": ("Ausgezogen", {"network_access": False,
                            "late_fee": False,
                            "semester_fee": True,
                            "reduced_semester_fee": True,
                            "mail": True}),

    "moved_from_division": ("Umzug aus anderer Sektion", {"registration_fee": False}),

    "already_paid": ("Semesterbeitrag in anderer Sektion entrichtet", {"semester_fee": False}),

    "root": ("Root", reduce(lambda d1,d2: dict(d1, **d2), [org_props,
                                                           finance_admin_props,
                                                           group_admin_props,
                                                           infra_admin_props,
                                                           {'mail': True}
                                                           ]))
}


status_groups_map = {
    1: ("member", "usertraffic"),  # bezahlt, ok
    2: ("member", "usertraffic"),  # angemeldet, aber nicht bezahlt
    3: ("away",),    # nicht bezahlt, hat nur Mail
    4: ("member", "usertraffic"),  # angemeldet, nicht bezahlt, 2. Warnung
    5: ("member", "suspended", "usertraffic"),  # angemeldet, nicht bezahlt, gesperrt
    6: ("away",),  # angemeldet, gesperrt (ruhend)
    7: ("member", "violator"),  # angemeldet, gesperrt (Verstoss gegen Netzordnung)
    8: (),  # ausgezogen, gesperrt
    9: (),  # Ex-Aktiver
    10: ("away",), # E-Mail, ehemals IP
    11: (),  # uebrig in Wu die in Renovierung
    12: ("member", "usertraffic")  # gesperrt wegen Trafficueberschreitung

}


site_name_map = {
    0: u"Wundtstraße/Zellescher Weg",
    1: u"Borsbergstraße",
    2: u"Zeunerstraße",
    3: u"Budapester Straße",
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
}

building_subnet_map = {
    # building_id: subnet_id
    1: 6,  # Wu5
    2: 3,  # Wu7
    3: 8,  # Wu9
    4: 7,  # Wu11
    5: 1,  # Wu1
    6: 2,  # Wu3
    7: 4,  # ZW41
    8: 4,  # ZW41A
    9: 4,  # ZW41B
    10: 4,  # ZW41C
    11: 4,  # ZW41D
    12: 10,  # Bor34
    #TODO: but the zeu1f has more than 1 subnet?
    # what does this affect?
    13: 11,  # Zeu1f
    # Zeu1f has also subnet#12, but this mapping is only used to determine the
    # default subnet.
    14: 13,  # Bu22
    15: 14,  # Bu24
}

vlan_name_vid_map = {
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
}
