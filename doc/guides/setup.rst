Setting up the project
======================

Cloning this directory
----------------------

A basic understanding of `git <https://git-scm.com/>`__ is advisable.
The first step should be to clone this repository via
``git clone --recursive <url>``, using what clone url shows you above
`this very readme <https://github.com/agdsn/pycroft>`__.


PyCharm Integration
-------------------

In order to integrate the setup into PyCharm, make sure that you are
using the Professional edition, because the Docker integration feature
is only available in the Professional edition of PyCharm. Also make sure
that you have updated to a recent version, there were important bug
fixes with regards to the Docker integration.

Project interpreters
~~~~~~~~~~~~~~~~~~~~

The **dev** and **test** environments should be added to PyCharm as
project interpreters.

Go to “Settings” → “Project: Pycroft” → “Project Interpreter” → Gear
icon → “Add remote” → “Docker Compose”.

Create a new server for your local machine (use the default settings for
that), if none exists yet. Select the config file
``docker-compose.dev.yml`` in the project root, select the the service:
``dev-app``, and type in the following path for the python interpreter:
``/opt/pycroft/venv/bin/python``.

Repeat the same thing for **test** environment defined in
``docker-compose.test.yml``.

Save, and make sure the correct interpreter (**dev**, not **test**) is
selected as default for the project (“Project settings” → “Project
interpreter”). As a proof of concept, you can run a “Python Console”
inside PyCharm.

Run Configurations
~~~~~~~~~~~~~~~~~~

A few run configurations are already included in the project’s ``.idea``
folder. If you have created the project interpreters according to the
above steps, the appropriate interpreters should have been autoselected
for each run configuration.

Database connections (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can access databases with PyCharm if you are so inclined. First, you
need to obtain the IP address of the database container. If you didn’t
change the project name, the following command will yield the IP address
of the database development container:

.. code:: bash

   docker inspect pycroft_dev-db_1 -f '{{ .NetworkSettings.Networks.pycroft_dev.IPAddress }}'

Make sure that database container is started, show the database pane in
PyCharm, and add a new data source. PyCharm may complain about missing
database drivers. Install any missing driver files directly through
PyCharm or your distribution’s package manager (whatever you prefer).
The password is ``password``.

Setting up the Database
-----------------------

For this section, double check that every container is up and running
via ``docker-compose ps``, and if necessary run ``docker-compose up -d``
again.

Pycroft needs a PostgreSQL database backend. The unit tests will
generate the schema and data automatically, but usually you want to run
your development instance against a recent copy of our current
production database.

The password for the ``postgres`` user is ``password``.

Importing the production database into Pycroft is a three-step process:

1. A regular dump is published in our `internal
   gitlab <https://git.agdsn.de/AGDSN/pycroft-data>`__.

   Clone this repository to your computer.

2. Import the dump:

   ``psql -h 127.0.0.1 -p 55432 -U postgres -d pycroft -f ../pycroft-data/pycroft.sql``

After all that, you should be able to log in into your pycroft instance
with the username ``agdsn`` at ``localhost:5000``. All users have the
password ``password``.

**Congratulations!**

To import a table from a CSV file, use:

``psql -h 127.0.0.1 -p 55432 -U postgres -d pycroft``

``\copy [tablename] from 'file.csv' with delimiter ',' csv header;"``

Running the test suite
----------------------

For the testing setup, there exists a separate docker-compose file:

.. code:: sh

   # get the stack up and running
   docker-compose -f docker-compose.test.yml up -d
   # run all the tests
   docker-compose -f docker-compose.test.yml run --rm test-app test
   # run only the frontend tests
   docker-compose -f docker-compose.test.yml run --rm test-app test tests.frontend

Making changes to the database schema
-------------------------------------

Pycroft uses `Alembic <http://alembic.zzzcomputing.com/>`__ to manage
changes to its database schema. On startup Pycroft invokes Alembic to
ensure that the database schema is up-to-date. Should Alembic detect
database migrations that are not yet applied to the database, it will
apply them automatically.

To get familiar with Alembic it is recommended to read the official
`tutorial <http://alembic.zzzcomputing.com/en/latest/tutorial.html>`__.

Creating a database migration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Migrations are python modules stored under
``pycroft/model/alembic/versions/``.

A new migration can be created by running:

::

   docker-compose run --rm dev-app alembic revision -m "add test table"

Alembic also has the really convenient feature to
`autogenerate <http://alembic.zzzcomputing.com/en/latest/autogenerate.html>`__
migrations, by comparing the current status of the database against the
table metadata of the application.

::

   docker-compose run --rm dev-app alembic revision --autogenerate -m "add complex test table"

The autogeneration does not know about trigger functions, view
definitons or the like. For this, you can pop up a python shell and
compile the statements yourself. This way, you can just copy-and-paste
them into ``op.execute()`` commands in the autogenerated schema upgrade.

.. code:: python

   import pycroft.model as m
   from sqlalchemy.dialects import postgresql
   print(m.ddl.CreateFunction(m.address.address_remove_orphans)
         .compile(dialect=postgresql.dialect()))
   # if the statement itself has no variable like `address_remove_orphans`,
   # you can try to extract it from the `DDLManager` instance:
   create_stmt, drop_stmt = [(c, d) for _, c, d in m.user.manager.objects
                             if isinstance(c, m.ddl.CreateTrigger)
                             and c.trigger.name == 'TRIGGER_NAME_HERE']
   print(create_stmt.compile(dialect=postgresql.dialect()))
   print(drop_stmt.compile(dialect=postgresql.dialect()))

Related dependencies
--------------------

Pycroft has dependencies that are not part of the Pycroft project, but
are maintained by the Pycroft team. Those are:

-  `wtforms-widgets <https://github.com/agdsn/wtforms-widgets>`__, for
   rendering forms

To make it easier to make changes on these dependencies, they are added
as submodule in the ``deps`` folder. You need to recursively clone this
repo in order to have them.

You can make changes in these sudmodules and deploy them (in your dev
environment) with:

::

   docker-compose run --rm dev-app pip install -r requirements.txt

The production build also uses the submodules. Make sure to update the
commit hash of the submodule HEAD if you change something. This will be
shown as unstaged change.

Additionally, new versions can be uploaded to PyPi by following these
steps:

-  Adjust setup.py (new version number, etc.)
-  Run the ``distribute.sh`` script afterwards in order to upload the
   new version to PyPi
