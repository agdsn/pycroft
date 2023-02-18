Docker architecture
-------------------

We provide three different container environments for the project:

dev
    Development environment. The container images contain
    helpful tools, the containers uses persistent volumes and your local
    project directory of your machine is mounted inside the container.
test
    Test environment. Almost identical to the development
    environment. Persistent volumes are replaces by *tmpfs* file systems
    for improved performance and ephemerality.
prod
    Production environment. Contains only what is required to
    run Pycroft without development tools.

For each environment a docker compose file is provided. The following
diagram shows all services/containers, images and volumes at a glance:

.. figure:: ../_static/Docker.svg
    :alt: Docker Architecture
    :width: 100%

    Docker Architecture

-  A ``base`` service/container for creating the base image
   ``agdsn/pycroft-base`` based on the Debian variant of Docker’s
   official Python image ``python``. The service/container is not
   actually needed, it’s only used to build the base image. The base
   image contains basic system software required to run Pycroft. A
   ``pycroft`` user and group with UID and GID specified as build
   arguments is created in the image. The UID and GID of this user
   should match with your user on your development machine, because the
   development service bind mounts the project directory on your local
   machine in the container. The home directory of the ``pycroft`` user
   is created user at ``/opt/pycroft``. A `virtual environment
   (venv) <https://docs.python.org/3/library/venv.html>`__ is created at
   ``/opt/pycroft/venv`` and automatically activated by the image’s
   entrypoint.
-  A ``dev-app`` service/container based on ``agdsn/pycroft-dev``
   derived from ``agdsn/pycroft-base``. The development image contains
   additional packages for development, e.g. ``gcc``, ``npm``. The
   service uses two persistent volumes:

   -  the home directory ``/opt/pycroft`` of the ``pycroft`` user, that
      contains among other things, the virtual environment, the pip
      cache, and the ``.bash_history``.
   -  the Pycroft sources on your local machine at ``/opt/pycroft/app``.

-  A ``test-app`` service/container based on the ``agdsn/pycroft-dev``
   image, that runs unit and integration tests. The database tests are
   run against an optimized in-memory database.
-  A ``prod-app`` service/container based on ``agdsn/pycroft-prod``,
   which is based on ``agdsn/pycroft-base`` that contains only the
   basics that are required for running Pycroft without development
   tools, such as ``gcc`` or ``npm``. Pycroft and its dependencies are
   build using an instance of the ``agdsn/pycroft-develop`` image using
   the `multi-stage
   builds <https://docs.docker.com/develop/develop-images/multistage-build/>`__
   feature of Docker.
-  A ``dev-db`` and ``test-db`` service/container based on the official
   ``postgresql`` image, that provides a development and test database
   respectively. The test database uses ``tmpfs`` for the data directory
   to improve performance. The dev database uses a persistent volume for
   the data directory.
-  A ``dev-ldap`` and ``test-ldap`` service/container based on the
   ``dinkel/openldap`` image, that provides a development and test LDAP
   server respectively.
-  A ``dev-mq`` and ``test-mq`` service/container based on the official
   ``rabbitq`` image, that provides a development and test message queue
   respectively.

The separate services for *dev* and *test* are mainly for isolation (you
don’t want tests to affect your development instance and vice versa) and
also for performance (unit tests should be quick). There are no
``prod-`` services for ``db``, ``ldap``, and ``mq``, because the
production instances of these services are typically managed outside of
Pycroft.

All services of the same type (**dev** and **test**) share the same
network namespace, i.e. you can reach the database server on
``127.0.0.1`` from ``dev-app`` although it’s running in a different
container.

The services are put into different compose files for convenience:

``docker-compose.base.yml``
    Common definitions of services
``docker-compose.dev.yml``
    Development services
``docker-compose.test.yml``
    Test services
``docker-compose.prod.yml``
    Production services

The **dev** environment is default environment. The default compose file
``docker-compose.yml`` is a symlink to ``docker-compose.dev.yml``.
