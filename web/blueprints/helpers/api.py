# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.model import session
from sqlalchemy.sql import func, Alias, literal_column, select


def json_agg(query):
    return session.session.query(func.json_agg(literal_column("row"))) \
        .select_from(Alias(query.subquery(), "row"))


def json_agg_core(selectable):
    return select([func.json_agg(literal_column("row"))]) \
        .select_from(selectable.alias("row"))