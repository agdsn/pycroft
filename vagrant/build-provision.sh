#!/bin/bash
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

#TODO: think of smart way to source provision.cfg, so that it can be shared across scripts
PROJDIR="/pycroft"
VAGRANTDIR="/vagrant"
USER="vagrant" #user that runs pycroft
DBNAME="pycroft.db"

#install necessary system packages
apt-get update
apt-get install -y git postgresql postgresql-client libpq-dev libsqlite3-dev python-dev python-pip python-software-properties
apt-add-repository 'deb http://ftp.us.debian.org/debian wheezy-backports main'
apt-get update
apt-get install -y nodejs
if [ ! -f /usr/bin/node ]; then
    ln -s /usr/bin/nodejs /usr/bin/node
fi
curl -L https://npmjs.org/install.sh | sh
npm install -g bower

if cd $PROJDIR && [[ $(git config --get remote.origin.url) == *Pycroft* ]]; then
    echo "Pycroft git repo found."
else
  echo "Error: Please make sure we are in <pycroft-git-repo>/vagrant"
  exit 1
fi

sudo -u $USER bower install -F

#install dependencies
echo "Installing required python modules..."
pip install -r $PROJDIR/requirements.txt || exit 1
pip install psycopg2

#install pre-commit pep8 check hook
#if [ -d $PROJDIR/.git/hooks ] && [ ! -f $PROJDIR/.git/hooks/pre-commit ]; then
#  #is a git repo, but no pre-commit hook currently set
#  echo "Installing PEP8 check pre-commit hook"
#  cp $PROJDIR/utils/pre-commit $PROJDIR/.git/hooks/pre-commit
#fi

echo "Configuring postgres..."
if [[ $(sudo -u postgres psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$USER'") != 1 ]]; then
    sudo -u postgres createuser $USER -ds > /dev/null
fi
if [[ $(sudo -u postgres psql -l | grep $DBNAME | wc -l) == 0 ]]; then
    sudo -u $USER createdb $DBNAME
fi

echo "Filling postgres DB with sample data..."
sudo -u $USER psql $DBNAME -f $PROJDIR/example/pg_example_data.sql > /dev/null

echo "All done! Starting Pycroft... (remember, :5000 => :5001)"
sudo -u $USER python2 $PROJDIR/server_run.py --debug --exposed &
