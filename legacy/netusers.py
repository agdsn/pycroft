# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker, scoped_session

from conn import conn_opts

import netusers_model as model

name = "netusers"

engine = create_engine('mysql://{netusers-user}:{netusers-password}@127.0.0.1'
                       ':{netusers-port}/netusers'.format(**conn_opts))
session = scoped_session(sessionmaker(bind=engine))
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
