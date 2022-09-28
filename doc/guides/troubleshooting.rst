Troubleshooting
===============

Due to laziness, prefix every bash-snippet with

.. code:: sh

   alias drc=docker-compose

Webpack appears to be missing a library
---------------------------------------

Re-Install everything using npm, and re-run the webpack entrypoint.

.. code:: sh

   drc run --rm dev-app shell npm ci
   drc run --rm dev-app webpack

Pip appears to be missing a dependency
--------------------------------------

Reinstall the pip requirements

.. code:: sh

   drc run --rm dev-app pip install -r requirements.txt

I need to downgrade the schema
------------------------------

.. code:: sh

   drc run --rm dev-app alembic downgrade $hash

Other problems (f.e. failing database initialization)
-----------------------------------------------------

.. code:: sh

   drc build
