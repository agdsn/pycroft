#!/bin/bash

#set -x

: ${SQL_PATH:=data/legacy.sql}

if [[ ! -f ${SQL_PATH} ]]; then
    echo please provide legacy sql unter ${SQL_PATH}
    exit 1
fi

COMPOSE="docker-compose  -f compose/default/docker-compose.yml"

${COMPOSE} up -d db
${COMPOSE} stop web


echo importing sql dump
${COMPOSE} exec --user=postgres db psql -v ON_ERROR_STOP=1 --file "/pycroft/${SQL_PATH}"

echo importing to pycroft database
${COMPOSE} run --rm web python3 -m legacy.import_legacy
