# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
display_schema
~~~~~~~~~~~~~~

This uses sqlalchemy-schemadisplay to draw the current mapped
database schema.

:copyright: (c) 2011 by AG DSN.
"""
from __future__ import print_function
from pycroft.model import _all
import sqlalchemy.exc
from sqlalchemy_schemadisplay import create_uml_graph
from sqlalchemy.orm import class_mapper

def fetch_mappers():
    # lets find all the mappers in our model
    mappers = []
    for attr in dir(_all):
        if attr[0] == '_': continue
        try:
            cls = getattr(_all, attr)
            mappers.append(class_mapper(cls))
        except Exception as ex:
            if isinstance(ex, sqlalchemy.exc.InvalidRequestError):
                if str(ex).startswith("One or more mappers failed to initialize"):
                    raise
            print("ignoring {}".format(attr))

    return mappers


def make_graph(mappers):
    # pass them to the function and set some formatting options
    graph = create_uml_graph(mappers,
        show_operations=True, # not necessary in this case
        show_multiplicity_one=True # some people like to see the ones, some don't
    )
    return graph

if __name__ == "__main__":
    mappers = fetch_mappers()
    graph = make_graph(mappers)

    graph.write_png('schema.png') # write out the file
    graph.write_svg('schema.svg') # write out the file
