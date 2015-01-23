#!/bin/bash
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

# Affected user: id 7934

timestamp() {
    date --date="$1" +"%Y-%m-%d"
}

random_amount() {
    shuf -i $[100*1024*1024]-$[2000*1024*1024] -n 1
}

for i in {0..20}
do
    echo "INSERT INTO traffic_volume (size, \"timestamp\", type, ip_id) VALUES($(random_amount), '$(timestamp "$i days ago") 00:00:00.000000', 'OUT', 1234);" | psql pycroft
done

for i in {21..41}
do
    echo "INSERT INTO traffic_volume (size, \"timestamp\", type, ip_id) VALUES($(random_amount), '$(timestamp "$[$i-21] days ago") 00:00:00.000000', 'IN', 1234);" | psql pycroft
done
