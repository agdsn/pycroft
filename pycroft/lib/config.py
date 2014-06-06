# -*- coding: utf-8 -*-

import json, collections, pkgutil
from os.path import isfile


class Config(object):
    def __init__(self):
        self._config_data = None
        self._package = "pycroft"
        self._resource = "config.json"

    def load(self):
        data = pkgutil.get_data(self._package, self._resource)
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
