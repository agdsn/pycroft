#!/bin/sh

#TODO: think of smart way to source provision.cfg, so that it can be shared across scripts
PROJDIR="/pycroft"
VAGRANTDIR="/vagrant"
USER="vagrant" #user that runs pycroft
DBNAME="pycroft.db"

#install necessary system packages
apt-get update
apt-get install -y git postgresql postgresql-client libpq-dev libsqlite3-dev python-dev python-pip

if cd $PROJDIR && [[ $(git config --get remote.origin.url) == *Pycroft* ]]; then
    echo "Pycroft git repo found."
else
  echo "Error: Please make sure we are in <pycroft-git-repo>/vagrant"
  exit 1
fi

#install dependencies
echo "Installing required python modules..."
pip install -r $PROJDIR/requirements.txt || exit 1

#install pre-commit pep8 check hook
#if [ -d $PROJDIR/.git/hooks ] && [ ! -f $PROJDIR/.git/hooks/pre-commit ]; then
#  #is a git repo, but no pre-commit hook currently set
#  echo "Installing PEP8 check pre-commit hook"
#  cp $PROJDIR/utils/pre-commit $PROJDIR/.git/hooks/pre-commit
#fi

echo "Configuring postgres..."
sudo -u postgres createuser $USER -ds
sudo -u $USER createdb $DBNAME

echo "Filling postgres DB with sample data..."
sudo -u $USER psql $DBNAME -f $PROJDIR/example/pg_schema.sql > /dev/null
sudo -u $USER psql $DBNAME -f $PROJDIR/example/pg_data.sql > /dev/null

echo "All done! Starting Pycroft... (remember, :5000 => :5001)"
sudo -u $USER python2 $PROJDIR/server_run.py --debug --exposed &
