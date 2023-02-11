Tests
=====

.. _running tests:

Running the test suite
----------------------
Requires
    * :ref:`docker environment <docker environment>`
    * Alternatively (unit tests only): a venv with installed test dependencies

For the testing setup, there exists a separate docker compose file:

There is a ``test`` subcommand of the docker entrypoint which wraps ``pytest``.
The ``legacy`` and pytest-based (``not legacy``) tests have to be run separately:

.. code:: sh

    docker compose run --rm test-app test -m "not legacy"
    docker compose run --rm test-app test -m "legacy"
    # or a single module:
    docker compose run --rm test-app test -m "not legacy" tests/helpers

Alternatively, in a ``shell`` or in your virtual environment,
you can just use ``pytest`` directly:

.. code:: sh

    docker compose run --rm test-app shell  # can be skipped for unit tests
    pytest -vm "not legacy" tests/helpers
