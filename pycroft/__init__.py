# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft
    ~~~~~~~~~~~~~~

    This package contains everything.

    :copyright: (c) 2011 by AG DSN.
"""

import json, collections, pkgutil

class Config(object):
    def __init__(self, fname=None):
        self._config_data = None
        self._package = "pycroft"
        self._resource = "config.json"

    def load(self):
        try:
            data = pkgutil.get_data(self._package, self._resource)
        except IOError:
            data = pkgutil.get_data(self._package, self._resource+".default")
        if data is None:
            raise Exception(
                "Could not load config file {1} "
                "from package {0}".format(self._package, self._resource)
            )
        self._config_data = json.loads(data)
        if not isinstance(self._config_data, collections.Mapping):
            raise Exception("Config must be a JSON object!")

    def __getitem__(self, key):
        if self._config_data is None:
            self.load()
        return self._config_data[key]

    def __setitem__(self, key, value):
        raise Exception("It is not possible to set configuration entries!")


config = Config()
