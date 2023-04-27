#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from pycroft.model.swdd import Tenancy
def get_tenancies_for_debitorenummer(debitor_nr: int):
    return Tenancy.q.filter_by(person_id=debitor_nr).all()

