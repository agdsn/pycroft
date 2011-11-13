#!/usr/bin/env python
# Copyright (c) 2011 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from migrate.versioning.shell import main
main(url='sqlite:///test_db.sqlite', debug='False', repository='migration')
