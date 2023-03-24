#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from sqlalchemy import Select, select, exists
from sqlalchemy.orm import Session


def row_exists(session: Session, stmt: Select) -> bool:
    return session.scalar(select(exists(stmt.add_columns(True))))
