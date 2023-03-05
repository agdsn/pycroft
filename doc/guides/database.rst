Database setup
==============

.. _imported dump:

Importing the database Dump
---------------------------
Prerequisites
    * :ref:`running containers`
    * Installed postgresql client

Pycroft needs a PostgreSQL database backend. The unit tests will
generate the schema and data automatically, but usually you want to run
your development instance against a recent copy of our current
production database.

The password for the ``postgres`` user is ``password``.

.. code:: shell

    # clone the anonymized dump into `data/`
    docker compose stop dev-app dev-webpack
    git clone https://git.agdsn.de/AGDSN/pycroft-data.git data --depth=1
    export PGPASSFILE=.pycroft.pgpass
    psql -wb postgres://postgres@127.0.0.1:55432/pycroft \
        -c '\set ON_ERROR_STOP 1' \
        -c 'drop schema if exists pycroft cascade' \
        -f data/pycroft_schema.sql \
        -f data/pycroft.sql
    # start the web app again
    docker compose start dev-app dev-webpack

Success
    Navigate to `<http://localhost:5000>`_.
    You should be able to login with user ``agdsn`` and password ``password``.

Open a psql shell
-----------------
Prerequisites
    * :ref:`running containers`

.. code:: shell

    # PW: `password`
    docker compose exec --user=postgres dev-db psql pycroft

Import a table from a CSV file
------------------------------
Prerequisites
    * :ref:`running containers`
    * Installed postgresql client

.. code-block:: bash

    psql -h 127.0.0.1 -p 55432 -U postgres -d pycroft \
        -c "\copy [tablename] from 'file.csv' with delimiter ',' csv header;"
