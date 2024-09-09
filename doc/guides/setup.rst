Minimal setup
=============

Using Docker
------------
The full dev-setup requires docker.

It is highly recommended to install
* `just <https://github.com/casey/just/releases>` ``≥1.23.0``

Follow the following guides:

#. :ref:`cloned repository`
#. :ref:`installed docker`

If you have ``just`` installed, just run `just setup`
and follow any leftover instructions.

Alternatively, follow these guides:

#. :ref:`docker environment`
#. :ref:`running containers`
#. :ref:`imported dump`

And possibly:

* :ref:`pycharm integration`


Using a python virtual environment (venv)
-----------------------------------------

Prerequisites
    * installed `uv <https://github.com/astral-sh/uv>`_

If you only want to build the documentation or run tests,
you only need to do the following:

#. :ref:`cloned repository`
#. Set up a virtual environment

   .. code:: shell

       uv venv
       uv pip sync requirements.dev.txt && uv pip install -e deps/wtforms-widgets -e '.[dev]'

#. Run tests / Build docs / …
