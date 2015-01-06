#!/bin/bash
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

#TODO: think of smart way to source provision.cfg, so that it can be shared across scripts
PROJDIR="/pycroft"
USER="vagrant" #user that runs pycroft
DBNAME="pycroft"
TESTS_DBNAME="pycroft_tests"
TMPFS_DIR="/mnt/tmpfs"
TMPFS_TABLESPACE_NAME="tmpfs"

echo "Running software provisioner. Run just this provisioner by issuing"
echo "        vagrant provision --provision-with=sw"

#install necessary system packages
apt-get update
apt-get install -y git postgresql postgresql-client libpq-dev libsqlite3-dev python-dev python-pip python-software-properties
apt-add-repository 'deb http://ftp.us.debian.org/debian wheezy-backports main'
apt-get update
apt-get install -y nodejs
if [[ ! -f /usr/bin/node ]]; then
    ln -s /usr/bin/nodejs /usr/bin/node
fi
if [[ ! -f $(which npm) ]]; then
    echo "Installing npm..."
    curl -L https://npmjs.org/install.sh | sh
fi
if [[ ! -f $(which bower) ]]; then
    echo "Installing bower..."
    npm install -g bower
fi

if cd $PROJDIR && [[ $(git config --get remote.origin.url) == *Pycroft* ]]; then
    echo "Pycroft git repo found."
else
    echo "Error: Please make sure \$PROJDIR (currently $PROJDIR) in the Vagrant VM is a Pycroft git repo"
    exit 1
fi

sudo -u $USER bower install -F
sudo -u $USER bower update -F

# install dependencies
echo "Installing required python modules..."
pip install -r $PROJDIR/requirements.txt || exit 1
pip install psycopg2 || exit 1
