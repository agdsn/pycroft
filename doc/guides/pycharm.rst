.. _pycharm integration:

PyCharm Integration
===================

Requires
    :ref:`docker environment <docker environment>`

In order to integrate the setup into PyCharm, make sure that you are
using the Professional edition, because the Docker integration feature
is only available in the Professional edition of PyCharm. Also make sure
that you have updated to a recent version, there were important bug
fixes with regards to the Docker integration.

Project interpreters
--------------------

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
------------------

A few run configurations are already included in the project’s ``.idea``
folder. If you have created the project interpreters according to the
above steps, the appropriate interpreters should have been autoselected
for each run configuration.

Database connections (optional)
-------------------------------

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
