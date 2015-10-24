#!/bin/sh
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
set -e
export PGDATA=/postgresql
export PGHOST=$PGDATA
export PGDATABASE=pycroft
PGVERSION=9.4
PGPATH=/usr/lib/postgresql/$PGVERSION
PYCROFT_EXAMPLE_DATA=/pycroft/example/pg_example_data.sql

if [ ! -f $PGDATA/postgresql.conf ]; then
    echo Initialising postgres data directory $PGDATA
    sudo -n mkdir -p $PGDATA
    sudo -n mount -t tmpfs -o size=192M,nr_inodes=8k,mode=0700,uid=vagrant,gid=vagrant,noexec,nodev,nosuid tmpfs $PGDATA
    $PGPATH/bin/initdb -A peer
    sed -i -e "s|#\?unix_socket_directories = '[A-Za-z0-9\/]*'|unix_socket_directories = '$PGDATA'|" $PGDATA/postgresql.conf
    sed -i -e 's|#\?temp_buffers = [0-9]\+MB|temp_buffers = 64MB|' $PGDATA/postgresql.conf
    sed -i -e 's|#\?shared_buffers = [0-9]\+MB|shared_buffers = 128MB|' $PGDATA/postgresql.conf
    sed -i -e 's|#\?fsync = on|fsync = off|' $PGDATA/postgresql.conf
    sed -i -e 's|#\?synchronous_commit = on|synchronous_commit = off|' $PGDATA/postgresql.conf
    sed -i -e 's|#\?full_page_writes = on|full_page_writes = off|' $PGDATA/postgresql.conf
    sed -i -e 's|#\?bgwriter_lru_maxpages = [0-9]\+|bgwriter_lru_maxpages = 0|' $PGDATA/postgresql.conf
    sed -i -e 's|#\?checkpoint_segments = [0-9]\+|checkpoint_segments = 1|' $PGDATA/postgresql.conf
    sed -i -e 's|#\?wal_keep_segments = [0-9]\+|wal_keep_segments = 0|' $PGDATA/postgresql.conf
    sed -i -e "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" $PGDATA/postgresql.conf
    echo "host all all samenet trust" >> $PGDATA/pg_hba.conf

    echo Setting up databases
    $PGPATH/bin/pg_ctl start -w
    createdb pycroft
    createdb pycroft_tests
    [ -f $PYCROFT_EXAMPLE_DATA ] && psql < $PYCROFT_EXAMPLE_DATA
    $PGPATH/bin/pg_ctl stop -w
fi

exec $PGPATH/bin/postgres

