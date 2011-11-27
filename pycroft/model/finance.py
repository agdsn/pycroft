# -*- coding: utf-8 -*-
"""
    pycroft.model.finance
    ~~~~~~~~~~~~~~

    This module contains the classes FinanceAccount, ...

    :copyright: (c) 2011 by AG DSN.
"""
from base import ModelBase
from sqlalchemy import ForeignKey
from sqlalchemy import Table, Column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Integer
from sqlalchemy.types import String


class FinanceAccount(ModelBase):
    name = Column(String(127))
