#!/bin/bash
echo "Creating /tmp/test.db using example_data.sql..."

rm /tmp/test.db -f
SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")
cat $SCRIPTPATH/example_data.sql | sqlite3 /tmp/test.db
