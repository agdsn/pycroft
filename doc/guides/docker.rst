Docker
======

.. _installed docker:

Installing Docker and Docker Compose
------------------------------------
Requires
    *nothing*
You need to install

* `Docker-engine <https://docs.docker.com/engine/install/>`__ ``≥17.06.0``
* `Docker Compose <https://docs.docker.com/compose/install/>`__ ``≥1.16.0``

If not the case, add yourself to the ``docker`` group with

.. code:: sh

   sudo usermod -aG docker $(whoami)

For the changes to take effect, you need to log out and log back in again.

Success
    If ``docker-compose config`` displays the current configuration

.. _docker environment:

Setting environment variables
-----------------------------
Requires
    * :ref:`cloned repository <cloned repository>`
    * :ref:`installed docker <installed docker>`

This is best done using the ``.env`` file
(see `the compose docs <https://docs.docker.com/compose/environment-variables/>`_).

.. code:: sh

    cp example.env .env
    sed -i "s/# *UID=.*$/UID=${UID}/" .env
    sed -i "s/# *GID=.*$/UID=${GID}/" .env


``TAG``
~~~~~~~

The tag of the images created by ``docker-compose`` can be specified
with the ``TAG`` environment variable, which defaults to ``latest``,
e.g.:

.. code:: bash

   TAG=1.2.3 docker-compose -f docker-compose.prod.yml build

This will tag all generated images with the tag ``1.2.3``.

.. _built images:

Building the images
-------------------
Requires
    * :ref:`docker environment <docker environment>`

.. code:: bash

    docker compose build

.. _running containers:

Starting the containers
-----------------------
Requires
    * :ref:`docker environment <docker environment>`

A complete environment can be started by running

.. code:: bash

   docker-compose up -d

This will start all *dev* environment. ``docker-compose`` will build
necessary images if not already present, it will *not* however
automatically rebuild the images if the ``Dockerfile``\ s or any files
used by them are modified.

If you run this command for the first time, this might take a while, as
a series of packages and image are downloaded, so grab a cup of tea and
relax.

All services, except ``base``, which is only used to build the
``agdsn/pycroft-base`` image, should now be marked as ``UP``, if you
take a look at ``docker-compose ps``. There you see which port
forwardings have been set up (remember the port ``web`` has been
exposed!)

Because you started them in detached mode, you will not see what they
print to stdout. You can inspect the output like this:

.. code:: sh

   docker-compose logs # for all services
   docker-compose logs dev-app  # for one service
   docker-compose logs -f --tail=50 dev-app  # Print the last 50 entries and follow the logs

The last command should tell you that the server spawned an instance at
0.0.0.0:5000 from inside the container.

**But don’t be too excited, pycroft will fail after the login – we have
to set up the database.**

To start another enviroment, run ``docker-compose`` with the\ ``-f``
flag to specify a different compose file, e.g.:

.. code:: bash

   docker-compose -f docker-compose.test.yml up -d

This would start the **test** environment.

(Re-)building/Pulling images
----------------------------

You can (re-)build/pull a particular service/image (or all of them if no
service is specified) by running:

.. code:: bash

   docker-compose build --force-rm --pull [service]
