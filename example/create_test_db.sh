#!/bin/bash
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
echo "Creating /tmp/test.db using example_data.sql..."

rm /tmp/test.db -f
SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")
cat $SCRIPTPATH/example_data.sql | sqlite3 /tmp/test.db
