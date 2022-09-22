pycroft
=======

.. contents:: Contents
    :local:

.. automodule:: pycroft
    :members:
    :undoc-members:
    :show-inheritance:

Subpackages
-----------
.. toctree::

    pycroft.model
    pycroft.lib
    pycroft.helpers

Submodules
----------
.. automodule:: pycroft.exc
.. automodule:: pycroft.property
    :undoc-members:
.. automodule:: pycroft.task
    :exclude-members: DBTask

    .. autoclass:: pycroft.helpers.task.DBTask
        :members:
        :exclude-members: ignore_result,priority,rate_limit,reject_on_worker_lost,request_stack,serializer,track_started,store_errors_even_if_ignored,typing
