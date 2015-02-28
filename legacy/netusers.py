# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker, scoped_session

from conn import conn_opts

import netusers_model as model

name = "netusers"

engine = create_engine(conn_opts['netusers'])
session = scoped_session(sessionmaker(bind=engine))

relevant_tables = [model.Wheim,
                  model.Hp4108Port,
                  model.Nutzer,
                  model.Computer,
                  model.Subnet,
                  model.Status,
                  model.Credit,
                  model.ZihIncident]
"""
+--------------------+
| Tables_in_netusers |
+--------------------+
| wheim              |
| hp4108_ports       |
| nutzer             |
| computer           |
| subnet             |
| status             |
| credit             |
| kabel              |
| new_accounts       |
| sperr_log          |
| versionen          |
| zih_incidents      |
+--------------------+
"""
