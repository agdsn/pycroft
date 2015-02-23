# -*- coding: utf-8 -*-
from sqlalchemy import Column, String
from pycroft.model.base import ModelBase

__author__ = 'Florian Österreich'


class TestTask(ModelBase):
    text = Column(String, nullable=False)
