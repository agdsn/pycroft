#!/bin/bash
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

#TODO: think of smart way to source provision.cfg, so that it can be shared across scripts
PROJDIR="/pycroft"
VAGRANTDIR="/vagrant"
USER="vagrant" #user that runs pycroft
DBNAME="pycroft"
TESTS_DBNAME="pycroft_tests"
TMPFS_DIR="/mnt/tmpfs"
TMPFS_TABLESPACE_NAME="tmpfs"

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
pip install psycopg2 || exit 1

if [[ $(sudo -u postgres psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$USER'") != 1 ]]; then
    sudo -u postgres createuser $USER -ds > /dev/null
fi

drop_db_if_exists() {
    if [[ $(sudo -u postgres bash -c "psql -l | grep $1 | wc -l") != 0 ]]; then
        echo "Dropping database $1"
        sudo -u $USER dropdb $1
    fi
}

recreate_db() {
    drop_db_if_exists $1
    echo "Creating database $1 (with arguments: ${@:2})"
    sudo -u $USER createdb $@
}

recreate_tmpfs_tablespace() {
    drop_db_if_exists $TESTS_DBNAME
    sudo -u postgres psql -d postgres -c "DROP TABLESPACE IF EXISTS $TMPFS_TABLESPACE_NAME;"

    if grep -qs "$TMPFS_DIR" /proc/mounts; then
        echo "Mountpoint $TMPFS_DIR exists, unmounting..."
        sudo umount -f $TMPFS_DIR
    else
        echo "Mountpoint $TMPFS_DIR does not exist, recreating it..."
        mkdir -p $TMPFS_DIR
    fi

    echo "Creating tmpfs mount at $TMPFS_DIR"
    sudo mount -t tmpfs -o size=512m tmpfs $TMPFS_DIR

    mkdir $TMPFS_DIR/pgdata
    sudo chown postgres:postgres $TMPFS_DIR/pgdata
    sudo chmod go-rwx $TMPFS_DIR/pgdata

    sudo -u postgres psql -d postgres -c "CREATE TABLESPACE $TMPFS_TABLESPACE_NAME LOCATION '$TMPFS_DIR/pgdata';"
    sudo -u postgres psql -d postgres -c "GRANT CREATE ON TABLESPACE $TMPFS_TABLESPACE_NAME TO $USER;"   
}

recreate_db $DBNAME

recreate_tmpfs_tablespace
recreate_db $TESTS_DBNAME --tablespace=$TMPFS_TABLESPACE_NAME

# import example-db created by "pg_dump -f /example/pg_example/data.sql $DBNAME"
echo "Filling postgres DB with sample data..."
sudo -u $USER psql $DBNAME -f $PROJDIR/example/pg_example_data.sql > /dev/null

#set config.json to postgres
# (but using an absolute link so it is only changed within vagrant)
if [[ -f $PROJDIR/pycroft/config.json ]]; then
    rm $PROJDIR/pycroft/config.json
fi
ln -s $PROJDIR/pycroft/config.json.postgres $PROJDIR/pycroft/config.json

echo "All done! You can start Pycroft by running"
echo "    vagrant ssh -c \"python2 $PROJDIR/server_run.py --debug --exposed\""
