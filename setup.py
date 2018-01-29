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
    version="0.1.0",
    packages=find_packages(exclude=["tests", "tests.*"]),
    entry_points={
        'console_scripts': [
            'pycroft = scripts.server_run:main',
            'pycroft_legacy_import = legacy.import_legacy:main',
            'pycroft_legacy_cache = legacy.cache_legacy:main',
            'pycroft_legacy_gerok_import = legacy_gerok.__main__',
            'pycroft_ldap_sync = ldap_sync.__main__',
            'pycroft_sync_exceeded_traffic_limits = scripts.sync_exceeded_traffic_limits:main',
        ]
    },

    author="The Pycroft Authors",
    description="AG DSN user management software",
    long_description=__doc__,
    license="Apache Software License",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet',
    ],
    url="http://github.com/agdsn/pycroft/",
)
