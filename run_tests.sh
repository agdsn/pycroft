#!/bin/sh
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
pip install coverage pylint
find . -name "*.pyc" -delete
PYCROFT_DB_URI=sqlite:///:memory: nosetests --with-xunit --with-coverage --cover-erase --cover-branches --cover-package=web,pycroft,legacy

