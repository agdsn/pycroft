"""
Pycroft
-------

Pycroft is the user management system of the AG DSN
(Arbeitsgemeinschaft Dresdner Studentennetz)

Notes for developers
--------------------

When editing this file, you need to re-build the docker image for the
changes to take effect.  On a running system, you can just execute
``pip install -e .`` to update e.g. console script names.
"""

from setuptools import setup, find_packages
setup(
    name="pycroft",
    version="0.1",
    packages=find_packages(exclude=["tests", "tests.*"]),
    entry_points={
        'console_scripts': [
            'pycroft = server_run:main',
            'pycroft_legacy_import = legacy.import_legacy:main',
            'pycroft_legacy_cache = legacy.cache_legacy:main',
            'pycroft_legacy_gerok_import = legacy_gerok.__main__',
            'pycroft_ldap_sync = ldap_sync.__main__',
        ]
    },

    # metadata for upload to PyPI
    author="AG DSN",
    description="AG DSN user management software",
    long_description=__doc__,
    license="MIT",
    url="http://github.com/agdsn/pycroft/",   # project home page, if any
)
