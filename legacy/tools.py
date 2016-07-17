# coding=utf-8
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from __future__ import print_function
import logging as std_logging
log = std_logging.getLogger('import')
import collections
import time
from sqlalchemy.orm import RelationshipProperty, ColumnProperty

class timed(object):
    def __init__(self, logger, thing="", **kwargs):
        self.logger = logger
        self.enter_msg = kwargs.get('enter_msg',
                                   "{thing}...").format(thing=thing)
        self.exit_msg = kwargs.get('exit_msg',
                                   "...{thing} took {{duration}} seconds.").format(thing=thing)

    def __enter__(self):
        self._t = time.time()
        self.logger.info(self.enter_msg)

    def __exit__(self, *args):
        if self.exit_msg is not None:
            self.logger.info(
                self.exit_msg.format(duration=(time.time()-self._t)))


def invert_dict(d):
    inv_d = {}
    for k, v in d.items():
        inv_d.setdefault(v, set()).add(k)
    return inv_d


class DependencyError(Exception):
    pass


class TranslationRegistry(object):
    # TODO sort by resource dependencies instead of pycroft model?
    _provides = {}
    _satisfies = collections.defaultdict(lambda: set())
    _requires = collections.defaultdict(lambda: set())

    def requires_function(self, *other_funcs):
        """Explicit dependence other functions"""
        def decorator(func):
            self._requires[func] = set(other_funcs)
            return func
        return decorator

    def provides(self, *metas, **kwargs):
        """main translation function to create given ModelMetas"""
        def decorator(func):
            for meta in metas:
                self._provides[meta.__table__] = func

                parent_tables = set(parent.__table__ for parent in meta.__bases__ if hasattr(parent, '__table__'))
                for fkc in meta.__table__.foreign_key_constraints:
                    if fkc.referred_table in parent_tables:
                        self._satisfies[func].update(fkc.columns)
            for instr_attr in kwargs.get('satisfies', ()):
                prop = instr_attr.property
                if isinstance(prop, ColumnProperty):
                    self._satisfies[func].update(prop.columns)
                elif isinstance(prop, RelationshipProperty):
                    self._satisfies[func].update(prop.local_columns)
                else:
                    raise NotImplementedError
            return func
        return decorator

    def _required_translations(self, func):
        translates = invert_dict(self._provides)[func]
        required = set()
        for table in translates:
            for fkc in table.foreign_key_constraints:
                if (fkc.referred_table not in translates and
                        not self._satisfies[func].issuperset(fkc.columns)):
                    try:
                        required.add(self._provides[fkc.referred_table])
                    except KeyError as e:
                        raise DependencyError(
                            "Nothing provides {reftable} "
                            "(referenced from fkey {srctable}.{fkeys}),"
                            "required by {funcname}".format(
                                reftable=fkc.referred_table.name,
                                srctable=fkc.table.name,
                                fkeys=fkc.column_keys,
                                funcname=func.__name__))

        required.update(self._requires[func])
        return required

    def requirement_graph(self):
        return {func: self._required_translations(func)
                for func in set(self._provides.values())}

    def sorted_functions(self):
        func_dep_map = self.requirement_graph()
        sorted_funcs = []

        # dependency-free funcs
        ready_funcs = set(func for func, deps in func_dep_map.items()
                          if not deps)
        while ready_funcs:
            # pop executed off ready_funcs and insert it in node_list
            executed = ready_funcs.pop()
            func_dep_map.pop(executed)
            sorted_funcs.append(executed)
            # find funcs which depend on executed
            from_selection = [func for func, deps in func_dep_map.items()
                              if executed in deps]
            for func in from_selection :
                # remove dependency
                func_dep_map[func].remove(executed)

                # if func has all its dependencies executed,
                if not func_dep_map[func]:
                    # it can be executed
                    ready_funcs.add(func)

        if func_dep_map:
            raise DependencyError("Cyclic dependencies present: {}".format(
                func_dep_map))
        else:
            return sorted_funcs
