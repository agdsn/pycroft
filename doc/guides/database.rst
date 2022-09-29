Database setup
==============

.. _imported dump:

Importing the database Dump
---------------------------
Requires
    * :ref:`running containers`
    * Installed postgresql client

Pycroft needs a PostgreSQL database backend. The unit tests will
generate the schema and data automatically, but usually you want to run
your development instance against a recent copy of our current
production database.

The password for the ``postgres`` user is ``password``.

.. code:: shell

    # clone the anonymized dump into `data/`
    git clone https://git.agdsn.de/AGDSN/pycroft-data.git data
    # stop the web app while we're filling in the db. PW: `password`
    docker compose stop dev-app dev-webpack
    # execute the dump
    psql -h 127.0.0.1 -p 55432 -U postgres -d pycroft -f data/pycroft.sql
    # start the web app again
    docker compose start dev-app

Success
    Navigate to `<http://localhost:5000>`_.
    You should be able to login with user ``agdsn`` and password ``password``.

Open a psql shell
-----------------
Requires
    * :ref:`running containers`

.. code:: shell

    # PW: `password`
    docker compose exec --user=postgres dev-db psql pycroft

Import a table from a CSV file
------------------------------
Requires
    * :ref:`running containers`
    * Installed postgresql client

.. code-block:: bash

    psql -h 127.0.0.1 -p 55432 -U postgres -d pycroft \
        -c "\copy [tablename] from 'file.csv' with delimiter ',' csv header;"
