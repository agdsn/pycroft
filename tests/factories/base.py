# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from factory.alchemy import SQLAlchemyModelFactory as Factory

from pycroft.model.session import session


class BaseFactory(Factory):
    class Meta:
        sqlalchemy_session = session
