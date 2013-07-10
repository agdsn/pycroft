# -*- coding: utf-8 -*-

import json, collections
from os.path import isfile


class Config(object):
    def __init__(self):
        self._configdata = None
        self._configpath = "../../example/test_config.json"

    def load(self):
        if not isfile(self._configpath):
            raise Exception(
                "The configfile does not exist at '" + self._configpath + "'!")
        self._configdata = json.load(open(self._configpath))
        if not isinstance(self._configdata, collections.Mapping):
            raise Exception("Config must be a JSON object!")

    def __getitem__(self, key):
        if self._configdata == None:
            self.load()
        return self._configdata[key]

    def __setitem__(self, key, value):
        raise Exception("It is not possible to set configuration entries!")


config = Config()


def get(key):
    return config[key]