#!/usr/bin/env python
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from migrate.versioning.shell import main

if __name__ == '__main__':
    main(url='sqlite:////tmp/test.db', debug='False')
