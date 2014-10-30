#!/bin/sh

#TODO: think of smart way to source provision.cfg, so that it can be shared across scripts
PROJDIR="/pycroft"
VAGRANTDIR="/vagrant"
USER="vagrant" #user that runs pycroft
DBNAME="pycroft.db"

echo "All done! Starting Pycroft... (remember, :5000 => :5001)"
sudo -u $USER python2 $PROJDIR/server_run.py --debug --exposed &
