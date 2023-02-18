Tests
=====

.. _running tests:

Running the test suite
----------------------
Prerequisites
    * :ref:`docker environment <docker environment>`
    * Alternatively (unit tests only): a venv with installed test dependencies

For the testing setup, there exists a separate docker compose file:

There is a ``test`` subcommand of the docker entrypoint which wraps ``pytest``.

.. code:: sh

    docker compose run --rm test-app test
    # or a single module:
    docker compose run --rm test-app test tests/helpers

Alternatively, in a ``shell`` or in your virtual environment,
you can just use ``pytest`` directly:

.. code:: sh

    docker compose run --rm test-app shell
    pytest -v tests/helpers

Markers
~~~~~~~
You can use markers to select or deselect certain tests, e.g. slow ones:

... code:: sh
    pytest -vm "not slow" tests

The markers are defined in the ``pyproject.toml`` (key ``tool.pytest.ini_options.markers``).
A test can be marked via the ``@pytest.mark`` decorator, e.g. ``@pytest.mark.slow``.
