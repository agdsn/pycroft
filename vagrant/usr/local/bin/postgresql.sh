#!/bin/sh
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
PGDATA=/postgresql
PGVERSION=9.1

set -e
if [ ! -f $PGDATA/postgresql.conf ]; then
    echo Initialising postgres data directory $PGDATA
    mkdir -p $PGDATA
    mount -t tmpfs -o size=192M,nr_inodes=8k,mode=0700,uid=vagrant,gid=vagrant,noexec,nodev,nosuid tmpfs $PGDATA
    sudo -u vagrant /usr/lib/postgresql/$PGVERSION/bin/initdb -D $PGDATA -A peer
    sed -i -e 's/#temp_buffers = 8MB/temp_buffers = 64MB/' $PGDATA/postgresql.conf
    sed -i -e 's/#fsync = on/fsync = off/' $PGDATA/postgresql.conf
    sed -i -e 's/#synchronous_commit = on/synchronous_commit = off/' $PGDATA/postgresql.conf
    sed -i -e 's/#full_page_writes = on/full_page_writes = off/' $PGDATA/postgresql.conf
    sed -i -e 's/#bgwriter_lru_maxpages = 100/bgwriter_lru_maxpages = 0   /' $PGDATA/postgresql.conf
    sed -i -e "s|#unix_socket_directory = ''|unix_socket_directory = '$PGDATA'|" $PGDATA/postgresql.conf
    echo Setting up databases
    sudo -u vagrant /usr/lib/postgresql/$PGVERSION/bin/pg_ctl start -w -D $PGDATA
    sudo -u vagrant createdb -h $PGDATA pycroft
    sudo -u vagrant createdb -h $PGDATA pycroft_tests
    sudo -u vagrant /usr/lib/postgresql/$PGVERSION/bin/pg_ctl stop -w -D $PGDATA
fi

exec sudo -u vagrant /usr/lib/postgresql/$PGVERSION/bin/postgres -D $PGDATA
