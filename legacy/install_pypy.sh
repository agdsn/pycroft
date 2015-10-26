#!/bin/bash
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
set -e

if [[ $EUID -ne 0 ]]; then
    echo "must be run as root"
    exit 1
fi

apt-get install pypy

curl -O https://bootstrap.pypa.io/get-pip.py
pypy get-pip.py

pypy -m pip install cffi psycopg2cffi
sed '/psycopg2/d;/pysqlite/d' /pycroft/requirements.txt | xargs -a - -n 1 pypy -m pip install
echo -e "from psycopg2cffi import compat\ncompat.register()" > /usr/local/lib/pypy2.7/dist-packages/psycopg2.py

chmod 777 -R /usr/local/lib/pypy2.7/dist-packages/psycopg2cffi # for some reason it needs write access
