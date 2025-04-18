Troubleshooting
===============

Due to laziness, prefix every bash-snippet with

.. code:: sh

   alias drc=docker compose

Webpack appears to be missing a library
---------------------------------------

Re-Install everything using npm, and restart the bundling

.. code:: sh

   drc run --rm dev-app bun i --frozen-lockfile
   drc run --rm dev-app bun run bundle

Pip appears to be missing a dependency
--------------------------------------

Reinstall the pip requirements

.. code:: sh

   drc run --rm dev-app uv sync --locked
   drc run --rm dev-app uv pip install -e . deps/wtforms-widgets

I need to downgrade the schema
------------------------------

.. code:: sh

   drc run --rm dev-app alembic downgrade $hash

Other problems (f.e. failing database initialization)
-----------------------------------------------------

.. code:: sh

   drc build
