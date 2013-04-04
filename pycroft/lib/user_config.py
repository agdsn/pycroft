# -*- coding: utf-8 -*-
# Copyright (c) 2013 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'Florian Österreich'

from datetime import timedelta

#if you enter 0 for end_date it is an infinite group membership
initial_groups = [
    dict(group_name="NegativKonto",
         dates=dict(start_date=timedelta(0), end_date=timedelta(days=31)))]
