#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import typing


Attributes = dict[str, str | typing.Collection[str]]
# Depending on the LDAP scheme, attributes may be single-valued or multi-valued
# (e.g. `mail`, `memberOf`, `objectClass` as opposed to `uid`)
# canonicalized to a list
NormalizedAttributes = dict[str, typing.Collection[str]]

#: An LDAP Distinguished Name
DN = typing.NewType('DN', str)


class LdapRecord(typing.TypedDict):
    dn: DN
    attributes: Attributes
