# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Select, SelectBase

from sqlalchemy.sql import func, literal_column, select


def json_agg_core(selectable: SelectBase) -> Select[tuple[list[dict]]]:
    return select(func.json_agg(literal_column("row"))) \
        .select_from(selectable.alias("row"))
