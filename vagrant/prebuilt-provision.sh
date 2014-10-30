#!/bin/sh
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

#TODO: think of smart way to source provision.cfg, so that it can be shared across scripts
PROJDIR="/pycroft"
VAGRANTDIR="/vagrant"
USER="vagrant" #user that runs pycroft
DBNAME="pycroft.db"

echo "All done! Starting Pycroft... (remember, :5000 => :5001)"
sudo -u $USER python2 $PROJDIR/server_run.py --debug --exposed &
