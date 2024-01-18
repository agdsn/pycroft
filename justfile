#! /usr/bin/env just
# To install `just`, see
# https://github.com/casey/just#packages

drc := "docker compose"
export COMPOSE_FILE := "docker-compose.dev.yml:docker-compose.test.yml"
export PGPASSFILE := ".pycroft.pgpass"
test-psql := drc + " exec --user=postgres test-db psql pycroft"
dev-psql := drc + " exec --user=postgres dev-db psql pycroft"
schemadir := justfile_directory() / "data"
sql_schema := schemadir / "pycroft_schema.sql"
sql_dump := schemadir / "pycroft.sql"

# test

[private]
default:
    just --list

# set up a working pycroft installation.
setup: _setup && build _schema-import schema-upgrade

_setup:
    git submodule init
    git submodule update
    pre-commit install

# like setup, just without building docker images
setup-no-build: _setup && _schema-import schema-upgrade

# builds the docker images
build:
    docker buildx bake

# initializes the dev db with the instance
[confirm("about to remove any current data in the dev instance. continue?")]
schema-import: _schema-import (alembic "upgrade" "head")

_schema-import: _ensure_schema_dir _stop_all (_up "dev-db")
    psql postgres://postgres@127.0.0.1:55432/pycroft \
    	--quiet --no-password -o /dev/null \
    	-c 'set client_min_messages to WARNING' \
        --echo-errors -c '\set ON_ERROR_STOP 1' \
    	-c '\echo dropping schema…' \
        -c 'drop schema if exists pycroft cascade' \
    	-c '\echo importing schema…' \
        -f {{ sql_schema }} \
    	-c '\echo importing dump…' \
        -f {{ sql_dump }} \
    	-c '\echo all done.'

_ensure_schema_dir:
    #!/usr/bin/env bash
    if [[ ! -d {{ schemadir }} ]]; then
    	echo "{{ schemadir }} does not exist! Please clone it from gitlab:"
    	echo "git clone git@git.agdsn.de:AGDSN/pycroft-data.git data"
    	exit 1
    fi

# runs pycroft. Do this after `setup`!
run: (_up "dev-app")

# spawn a shell in the `test-app` container
test-shell *args:
    {{ drc }} run --rm test-app shell {{ args }}

# spawn a shell in the `dev-app` container
dev-shell *args:
    {{ drc }} run --rm dev-app shell {{ args }}

# run an alembic command against the `dev-db`
alembic command *args:
    {{ drc }} --progress=none run --rm dev-app alembic {{ command }} {{ args }}

# run an interactive postgres shell in the dev-db container
dev-psql *args="-f -": (_up "dev-db")
    {{ dev-psql }} -c 'set search_path=pycroft,public' {{ args }}

# run an interactive postgres shell in the test-db container
test-psql *args="-f -": (_up "test-db")
    {{ test-psql }} -c 'set search_path=pycroft,public' {{ args }}

# give a quick overview over the schema in the dev-db.

# requires the schema to be imported (see `import-schema`).
schema-status: (_up "dev-db")
    @echo "Schema version in dev-db: " \
    	`{{ dev-psql }} -q -t -c 'table pycroft.alembic_version'`
    @echo "Schema version in {{ sql_dump }}: " \
    	`grep 'COPY.*alembic_version' -A1 {{ sql_dump }} | sed -n '2p'`
    {{ drc }} --progress=none run --rm dev-app alembic check 2>&1 | tail -n1

# upgrade the (imported or created) schema to the current revision
schema-upgrade: (_up "dev-db") (alembic "upgrade" "head")

_stop_all:
    {{ drc }} --progress=quiet stop

_up +containers:
    {{ drc }} up --wait {{ containers }}
