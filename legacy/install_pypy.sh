#!/bin/bash
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
set -e

if [[ -z $(grep "docker" /proc/self/cgroup) ]]; then
    echo "must be run within the docker container"
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "must be run as root"
    exit 1
fi

echo -e "deb     http://ftp.de.debian.org/debian/    testing main contrib non-free\ndeb-src http://ftp.de.debian.org/debian/    testing main contrib non-free\ndeb     http://security.debian.org/         testing/updates  main contrib non-free" > /etc/apt/sources.list.d/testing.list
apt-get update
apt-get -t testing install pypy pypy-lib pypy-dev # to get pypy>2.6, importer broken with stable's pypy 2.4
# pypy-lib contains cffi

curl -O https://bootstrap.pypa.io/get-pip.py
pypy get-pip.py

pypy -m pip install psycopg2cffi==2.7.4
sed '/psycopg2/d;/pysqlite/d' ../requirements.txt > pypy_requirements.txt
pypy -m pip install -r pypy_requirements.txt

echo "Applying psycopg2 to psycopg2cffi compatibility fix" 
echo -e "from psycopg2cffi import compat\ncompat.register()" > /usr/local/lib/pypy2.7/dist-packages/psycopg2.py

chmod 777 -R /usr/local/lib/pypy2.7/dist-packages/psycopg2cffi # for some reason it needs write access

echo "Successfully finished!"
