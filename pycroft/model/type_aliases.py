#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import typing as t

from sqlalchemy import func
from sqlalchemy.orm import mapped_column

from pycroft.helpers import utc
from pycroft.model.types import DateTimeTz

str40 = t.Annotated[str, 40]
str50 = t.Annotated[str, 50]
str127 = t.Annotated[str, 127]
str255 = t.Annotated[str, 255]

datetime_tz = t.Annotated[
    utc.DateTimeTz,
    mapped_column(
        DateTimeTz,
        server_default=func.current_timestamp(),
    ),
]
datetime_tz_onupdate = t.Annotated[
    utc.DateTimeTz,
    mapped_column(
        DateTimeTz,
        server_default=func.current_timestamp(),
        # caution: this is not server_onupdate!
        onupdate=func.current_timestamp(),
    ),
]

mac_address = t.Annotated[str, 10]
