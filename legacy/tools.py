# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import collections
import functools

class memoized(object):
    # from https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
    """
    Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, arg):
        if not isinstance(arg, collections.Hashable):
            # uncachable. a list, for instance.
            # better to not cache than blow up.
            return self.func(arg)
        if arg in self.cache:
            return self.cache[arg]
        else:
            value = self.func(arg)
            self.cache[arg] = value
            return value

    def __get__(self, obj, objtype):
        """Support instance methods."""
        return functools.partial(self.__call__, obj)
