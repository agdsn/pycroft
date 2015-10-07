# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
member_props = {"network_access": True,
                "semester_fee": True,
                "late_fee": True,
                "registration_fee": True}

org_props = {"user_show": True,
             "user_change": True,
             "user_mac_change": True,
             "finance_show": True}

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

    "moved_out": ("Ausgezogen", {"network_access": False,
                                 "semester_fee": False,
                                 "late_fee": False}),

    "away": ("Zeitweise ausgezogen", {"network_access": False,
                                      "late_fee": False}),

    "moved_from_division": ("Umzug aus anderer Sektion", {"registration_fee": False}),

    "already_paid": ("Semesterbeitrag in anderer Sektion entrichtet", {"semester_fee": False}),

    "root": ("Root", reduce(lambda d1,d2: dict(d1, **d2), [org_props,
                    finance_admin_props, group_admin_props, infra_admin_props]))
}
