# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Column, String, UniqueConstraint

from pycroft.model.base import IntegerIdModel


DEFAULT_CITY = "Dresden"
DEFAULT_STATE = "Sachsen"
DEFAULT_COUNTRY = "Germany"

class Address(IntegerIdModel):
    street = Column(String(), nullable=False)
    number = Column(String(), nullable=False)
    addition = Column(String())
    # Sometimes, zipcodes can contain things like dashes, so rather take String().
    # we could probably impose some format by a check but that would be over engineering
    zip_code = Column(String(), nullable=False)
    city = Column(String(), nullable=False, server_default=DEFAULT_CITY)
    state = Column(String(), nullable=False, server_default=DEFAULT_STATE)
    country = Column(String(), nullable=False, server_default=DEFAULT_COUNTRY)

    __table_args__ = (
        UniqueConstraint('street', 'number', 'addition', 'zip_code', 'city', 'state', 'country'),
    )
