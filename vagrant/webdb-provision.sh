#!/bin/bash
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

#TODO: think of smart way to source provision.cfg, so that it can be shared across scripts
PROJDIR="/pycroft"
VAGRANTDIR="/vagrant"
USER="vagrant" #user that runs pycroft
DBNAME="pycroft.db"
TESTS_DBNAME="tests.db"

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
    echo "Error: Please make sure we are in <pycroft-git-repo>/vagrant"
    exit 1
fi

sudo -u $USER bower install -F
sudo -u $USER bower update -F

#install dependencies
echo "Installing required python modules..."
pip install -r $PROJDIR/requirements.txt || exit 1

echo "Configuring postgres..."
recreate_db_as() {
    if [[ $(sudo -u postgres psql -l | grep $1 | wc -l) == 0 ]]; then
        echo "Database $1 does not exist, creating it."
        sudo -u $2 createdb $1
    fi
}

if [[ $(sudo -u postgres psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$USER'") != 1 ]]; then
    sudo -u postgres createuser $USER -ds > /dev/null
fi
recreate_db_as $DBNAME $USER
recreate_db_as $TESTS_DBNAME $USER

echo "Filling postgres DB with sample data..."
sudo -u $USER psql $DBNAME -f $PROJDIR/example/pg_example_data.sql

#set config.json to postgres
if [[ -f $PROJDIR/pycroft/config.json ]]; then
    rm $PROJDIR/pycroft/config.json
fi
ln -s $PROJDIR/pycroft/config.json $PROJDIR/pycroft/config.json.postgres

echo "All done! Starting Pycroft... (remember, :5000 => :5001)"
sudo -u $USER python2 $PROJDIR/server_run.py --debug --exposed &
