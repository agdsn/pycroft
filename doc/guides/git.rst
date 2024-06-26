Git
===

.. _cloned repository:

Cloning the repository
----------------------
Prerequisites
    * A basic understanding of `git <https://git-scm.com/>`__
    * `pre-commit <https://pre-commit.com/>`__

.. code:: shell

    git clone --recursive https://github.com/agdsn/pycroft.git
    cd pycroft
    pre-commit install  # to install the pre-commit hooks

Contributing to dependencies
----------------------------
Prerequisites
    * :ref:`built images <built images>`

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

   docker compose run --rm dev-app pip sync requirements.txt

The production build also uses the submodules. Make sure to update the
commit hash of the submodule HEAD if you change something. This will be
shown as unstaged change.

Additionally, new versions can be uploaded to PyPi by following these
steps:

-  Adjust setup.py (new version number, etc.)
-  Run the ``distribute.sh`` script afterwards in order to upload the
   new version to PyPi
