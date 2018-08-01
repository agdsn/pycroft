# -*- coding: utf-8 -*-
# Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from pycroft.model.base import IntegerIdModel
from sqlalchemy import Column, Text, func
from pycroft.model.session import session
from pycroft.model.types import DateTimeTz

class WebStorage(IntegerIdModel):
    data = Column(Text, nullable=False)
    expiry = Column(DateTimeTz, nullable=False)

    @staticmethod
    def auto_expire():
        """Delete all expired items from the database"""
        WebStorage.q.filter(WebStorage.expiry <= func.current_timestamp()).delete(False)
        session.commit()
