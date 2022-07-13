#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import typing


Attributes = dict[str, str | typing.Collection[str]]


class LdapRecord(typing.TypedDict):
    dn: str
    attributes: Attributes
