#!/usr/bin/env just
# To install `just`, see
# https://github.com/casey/just#packages

# execute `just --evaluate <var>` to check the values of the variables set below
drc := "docker compose"
export COMPOSE_FILE := "docker-compose.dev.yml:docker-compose.test.yml"
export PGPASSFILE := ".pycroft.pgpass"
psql_pycroft_uri := "postgresql:///pycroft?options=-csearch_path%3Dpycroft,public"
test-psql := drc + " exec --user=postgres test-db psql " + "'" + psql_pycroft_uri + "'"
dev-psql := drc + " exec --user=postgres dev-db psql " + "'" + psql_pycroft_uri + "'"
schemadir := justfile_directory() / "data"
sql_schema := schemadir / "pycroft_schema.sql"
sql_dump := schemadir / "pycroft.sql"
swdd := justfile_directory() / "docker" / "db" / "docker-entrypoint-initdb.d" / "swdd.sql"

# test

[private]
default:
    just --list

# ansi codes: bold yellow / reset
_a_by := "\\e[1;33m"
_a_rst := "\\e[0m"

# set up a working pycroft installation.
setup: _setup && build _schema-import schema-upgrade
    @echo -e "{{ _a_by }}About to build all docker images. This may take a while.{{ _a_rst }}"
    @echo "If you wish to skip this, run \`setup-no-build\` instead."

local-setup:
    uv sync --locked
    uv pip install -e . -e deps/wtforms-widgets

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
schema-import: _confirm-drop _schema-import (alembic "upgrade" "head") _create-swdd-view

# creates the `swdd_vv` materialized view (→ `swdd.swdd_vv`)
_create-swdd-view:
    psql -wb postgres://postgres@127.0.0.1:55432/pycroft -c 'create materialized view if not exists swdd_vv as \
    SELECT swdd_vv.persvv_id, \
           swdd_vv.person_id, \
           swdd_vv.vo_suchname, \
           swdd_vv.person_hash, \
           swdd_vv.mietbeginn, \
           swdd_vv.mietende, \
           swdd_vv.status_id \
    FROM swdd.swdd_vv; \
    ALTER materialized view swdd_vv owner to postgres;'

_confirm-drop:
    #!/usr/bin/env bash
    read -p "Möchten Sie die Datenbank neu importieren? (j/N) " -n 1 con;
    echo;
    if [[ ! $con =~ [Jj] ]]; then
        echo "Datenbanklöschung abgebrochen.";
        exit 1;
    fi

_schema-import: _ensure_schema_dir _stop_all (_up "dev-db")
    chmod 0600 .pycroft.pgpass
    psql postgres://postgres@127.0.0.1:55432/pycroft \
      --quiet --no-password -o /dev/null \
      -c 'set client_min_messages to WARNING' \
      --echo-errors -c '\set ON_ERROR_STOP 1' \
      -c '\echo dropping schema…' \
      -c 'drop schema if exists pycroft cascade' \
      -f {{ swdd }} \
      -c '\echo importing schema…' \
      -f {{ sql_schema }} \
      -c '\echo importing dump…' \
      -f {{ sql_dump }} \
      -c '\echo all done.'

_ensure_schema_dir:
    #!/usr/bin/env bash
    if [[ ! -d {{ schemadir }} ]]; then
    	echo "{{ schemadir }} does not exist! Please clone it from gitlab:"
    	echo "git clone --depth 1 git@git.agdsn.de:AGDSN/pycroft-data.git data"
    	exit 1
    fi

# runs pycroft. Do this after `setup`!
run: (_up "dev-app")

# spawn a shell in the `test-app` container
[positional-arguments]
test-shell *args:
    {{ drc }} run --rm test-app shell "$@"

# spawn a shell in the `dev-app` container
[positional-arguments]
dev-shell *args:
    {{ drc }} run --rm dev-app shell "$@"

# run an alembic command against the `dev-db`
[positional-arguments]
alembic *args:
    {{ drc }} --progress=none run --rm dev-migrate shell flask alembic "$@"


# run an interactive postgres shell in the dev-db container
[positional-arguments]
dev-psql *args: (_up "dev-db")
    {{ dev-psql }} "$@"

# run an interactive postgres shell in the test-db container
[positional-arguments]
test-psql *args: (_up "test-db")
    {{ test-psql }} "$@"

# give a quick overview over the schema in the dev-db.

# requires the schema to be imported (see `import-schema`).
schema-status: (_up "dev-db")
    @echo "Schema version in dev-db: " \
    	`{{ dev-psql }} -q -t -c 'table pycroft.alembic_version'`
    @echo "Schema version in {{ sql_dump }}: " \
    	`grep 'COPY.*alembic_version' -A1 {{ sql_dump }} | sed -n '2p'`
    {{ drc }} --progress=none run --rm dev-app flask alembic check 2>&1 | tail -n1

schema-diff: (_up "dev-db") (alembic "diff")

# upgrade the (imported or created) schema to the current revision
schema-upgrade: (_up "dev-db") (alembic "upgrade" "head")

# regenerate `uv.lock`
deps-compile:
    uv lock

_stop_all:
    {{ drc }} --progress=quiet stop

_up +containers:
    {{ drc }} up --wait {{ containers }}

show_emails:
    {{ drc }} --progress=none up -d dev-celery-worker dev-mail
    {{ drc }} logs --no-log-prefix -f dev-mail

stop: 
    {{ drc }} stop
