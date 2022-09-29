.. Pycroft documentation master file, created by
   sphinx-quickstart on Thu Nov  3 20:56:59 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Pycroft's documentation!
===================================

Contents:

.. toctree::
   :maxdepth: 2

   self

Guides
------
.. toctree::
    :caption: Guides
    :maxdepth: 1

    guides/setup
    guides/git
    guides/docker
    guides/pycharm
    guides/troubleshooting
    guides/celery

Reference Documentation
-----------------------
.. toctree::
   :caption: Reference documentation
   :maxdepth: 2

   api/pycroft
   api/ldap_sync


Indices and tables
------------------

.. toctree::
   :caption: Indices and tables

   genindex
   modindex
   search

Architecture decision records
-----------------------------

.. toctree::
   :caption: Architecture decision records
   :name: ADRs
   :maxdepth: 1
   :glob:

   ADR001 – Use jQuery in typescript modules exclusively <arch/adr-001.rst>
   ADR002 - Continue using pickle as default serializer <arch/adr-002.rst>
   ADR003 - Use ``.table_valued`` wrapper for table valued sql functions <arch/adr-003.rst>
   ADR004 - Deprecate usage of ``session`` proxy in favor of dependency injection <arch/adr-004.rst>
   ADR005 - Improved exception handling in views <arch/adr-005.rst>
   arch/*
