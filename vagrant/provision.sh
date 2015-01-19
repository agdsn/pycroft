#!/bin/bash
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

set -e
DEBIAN_FRONTEND=noninteractive

cp -a /pycroft/vagrant/etc/apt/sources.list /etc/apt/
apt-get update
apt-get install -y git postgresql postgresql-client libpq-dev sqlite3 libsqlite3-dev python-dev python-pip nodejs supervisor sysv-rc sysvinit-utils
[ -f /usr/bin/node ] || ln -s /usr/bin/nodejs /usr/bin/node
service postgresql stop
update-rc.d postgresql remove

cp -a /pycroft/vagrant/etc/supervisor/conf.d/postgresql.conf /etc/supervisor/conf.d/
cp -a /pycroft/vagrant/usr/local/bin/postgresql.sh /usr/local/bin/postgresql.sh
service supervisor restart

cp -a /pycroft/vagrant/etc/profile.d/. /etc/profile.d/

echo "Installing npm"
which npm || curl -s -L https://npmjs.org/install.sh | sh

echo "Installing bower"
which bower || npm install -g bower

echo "Installing python packages..."
pip install -r /pycroft/vagrant/requirements.txt

echo "Installing JavaScript dependencies"
cd /pycroft
sudo -u vagrant bower install -F
sudo -u vagrant bower update -F
