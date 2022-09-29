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


.. _built images:

Building the dev images
-----------------------
Requires
    * :ref:`docker environment <docker environment>`

.. code:: bash

    docker compose build

Building the production images
------------------------------
Requires
    * :ref:`docker environment <docker environment>`

The tag of the images created by ``docker compose`` can be specified
with the ``TAG`` environment variable, which defaults to ``latest``,
e.g.:

.. code:: bash

   TAG=1.2.3 docker-compose -f docker-compose.prod.yml build

This will tag all generated images with the tag ``1.2.3``.


.. _running containers:

Starting the containers
-----------------------
Requires
    * :ref:`docker environment <docker environment>`

A complete environment can be started by running

.. code:: bash

   docker-compose up -d

If you run this command for the first time, this might take a while, as
the images have to be built (see :ref:`built images`)

Success
    * If ``docker compose ps`` show ``dev-`` and ``test-``\ -services as ``UP``
    * If logs show no errors (see :ref:`viewing logs`)


.. _viewing logs:

Viewing logs
------------
.. code:: sh

   docker-compose logs # for all services
   docker-compose logs dev-app  # for one service
   docker-compose logs -f --tail=50 dev-app  # Print the last 50 entries and follow the logs


(Re-)building/Pulling images
----------------------------

You can (re-)build/pull a particular service/image (or all of them if no
service is specified) by running:

.. code:: bash

   docker-compose build --force-rm --pull [service]
