#!/bin/sh
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
set -e
export PGDATA=/postgresql
export PGHOST=$PGDATA
export PGDATABASE=pycroft
PGVERSION=9.1

if [ ! -f $PGDATA/postgresql.conf ]; then
    echo Initialising postgres data directory $PGDATA
    sudo -n mkdir -p $PGDATA
    sudo -n mount -t tmpfs -o size=192M,nr_inodes=8k,mode=0700,uid=vagrant,gid=vagrant,noexec,nodev,nosuid tmpfs $PGDATA
    /usr/lib/postgresql/$PGVERSION/bin/initdb -A peer
    sed -i -e 's/#temp_buffers = 8MB/temp_buffers = 64MB/' $PGDATA/postgresql.conf
    sed -i -e 's/#fsync = on/fsync = off/' $PGDATA/postgresql.conf
    sed -i -e 's/#synchronous_commit = on/synchronous_commit = off/' $PGDATA/postgresql.conf
    sed -i -e 's/#full_page_writes = on/full_page_writes = off/' $PGDATA/postgresql.conf
    sed -i -e 's/#bgwriter_lru_maxpages = 100/bgwriter_lru_maxpages = 0   /' $PGDATA/postgresql.conf
    sed -i -e "s|#unix_socket_directory = ''|unix_socket_directory = '$PGDATA'|" $PGDATA/postgresql.conf
    echo Setting up databases
    /usr/lib/postgresql/$PGVERSION/bin/pg_ctl start -w
    createdb pycroft
    createdb pycroft_tests
    /usr/lib/postgresql/$PGVERSION/bin/pg_ctl stop -w
fi

exec /usr/lib/postgresql/$PGVERSION/bin/postgres

