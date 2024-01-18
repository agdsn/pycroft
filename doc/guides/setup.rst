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
    * `virtualenvwrapper <https://virtualenvwrapper.readthedocs.io/en/latest/>`_
      (`arch:python-virtualenvwrapper <https://archlinux.org/packages/?name=python-virtualenvwrapper>`_,
      `debian:virtualenvwrapper <https://packages.debian.org/bullseye/virtualenvwrapper>`_)

If you only want to build the documentation or run tests,
you only need to do the following:

#. :ref:`cloned repository`
#. Set up a virtual environment

   .. code:: shell

       mkvirtualenv -a . -r requirements.txt -r requirements.dev.txt pycroft
       pip install -r requirements.txt -r requirements.dev.txt

#. Run tests / Build docs / …
