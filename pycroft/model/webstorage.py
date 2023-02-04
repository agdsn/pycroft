# Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.webstorage
~~~~~~~~~~~~~~~~~~~~~~~~
"""
from sqlalchemy import func, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from pycroft.helpers import utc
from pycroft.model.base import IntegerIdModel
from pycroft.model.session import session


class WebStorage(IntegerIdModel):
    data: Mapped[bytes] = mapped_column(LargeBinary)
    expiry: Mapped[utc.DateTimeTz]

    @staticmethod
    def auto_expire() -> None:
        """Delete all expired items from the database"""
        WebStorage.q.filter(WebStorage.expiry <= func.current_timestamp()).delete(False)
        session.commit()
