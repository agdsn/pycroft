# -*- coding: utf-8 -*-
# Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from pycroft.model.base import IntegerIdModel
from sqlalchemy import Column, DateTime, Text
from datetime import datetime
from pycroft.model.session import session

class WebStorage(IntegerIdModel):
    data = Column(Text, nullable=False)
    expiry = Column(DateTime, nullable=False)

    @staticmethod
    def auto_expire():
        WebStorage.q.filter(WebStorage.expiry <= datetime.utcnow()).delete(False)
        session.commit()
