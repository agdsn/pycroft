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

echo "Running database provisioner. Run just this provisioner by issuing"
echo "        vagrant provision --provision-with=db"

create_db() {
    echo "Creating database $1 (with arguments: ${@:2})"
    sudo -u $USER createdb $@
}

create_tmpfs_tablespace() {
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

# recreate database cluster
echo "Configuring postgres..."
sudo -u postgres pg_dropcluster --stop 9.1 main || exit 1
sudo -u postgres pg_createcluster 9.1 main

# configure postgres to allow connections from vm host
pg_auth_string="host all all samenet md5"
pg_auth_configfile="/etc/postgresql/9.1/main/pg_hba.conf"
pg_configfile="/etc/postgresql/9.1/main/postgresql.conf"
echo $pg_auth_string >> $pg_auth_configfile
sudo -u postgres sed -i s/"^[\#]\?listen_addresses = 'localhost'"/"listen_addresses = '*'"/g $pg_configfile

sudo /etc/init.d/postgresql start

# add user to postgres
sudo -u postgres createuser $USER -ds > /dev/null
sudo -u postgres psql -d postgres -c "ALTER USER $USER WITH ENCRYPTED PASSWORD '$USER';"


create_db $DBNAME

create_tmpfs_tablespace
create_db $TESTS_DBNAME --tablespace=$TMPFS_TABLESPACE_NAME

# import example-db created by "pg_dump -f /example/pg_example/data.sql $DBNAME"
echo "Filling postgres DB with sample data..."
sudo -u $USER psql $DBNAME -f $PROJDIR/example/pg_example_data.sql > /dev/null

# set persistent environment variables
if ! grep -Fq "PYCROFT_DB_URI" /home/$USER/.profile;
then
    echo "export PYCROFT_DB_URI=postgresql+psycopg2:///$DBNAME?host=/var/run/postgresql" >> /home/$USER/.profile
fi

if ! grep -Fq "PYTHONPATH" /home/$USER/.profile;
then
    echo "export PYTHONPATH=$PYTHONPATH:/pycroft" >> /home/$USER/.profile
fi

echo "All done! You can start Pycroft by running"
echo "    vagrant ssh -c \"python2 $PROJDIR/server_run.py --debug --exposed\""
