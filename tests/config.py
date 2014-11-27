# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'jfalke'


import getpass


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


def get_database_uri():
    user = getpass.getuser()
    postgres_test_uri = ("postgresql+psycopg2:///tests.db"
                         "?host=/var/run/postgresql")
    sqlite_test_uri = "sqlite:///:memory:"
    if user not in ['vagrant']:
        return sqlite_test_uri
    return postgres_test_uri


test_config = AttrDict({
    "database_uri": get_database_uri()
})
