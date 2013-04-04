# -*- coding: utf-8 -*-
__author__ = 'Florian Österreich'

from datetime import timedelta

#if you enter 0 for end_date it is an infinite group membership
initial_groups = [
    dict(group_name="NegativKonto",
         dates=dict(start_date=timedelta(0), end_date=timedelta(days=31)))]
