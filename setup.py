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
    author="The Pycroft Authors",
    description="AG DSN user management software",
    long_description=__doc__,
    version="0.1.0",
    url="http://github.com/agdsn/pycroft/",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    zip_safe=False,
    python_requires=">= 3.4",
    install_requires=[
        'alembic',
        'celery ~= 3.1.25',
        'Flask',
        'Flask-Babel',
        'Flask-Login',
        'Flask-WTF',
        'fints',
        'Jinja2',
        'MarkupSafe',
        'SQLAlchemy >= 1.1',
        'WTForms',
        'Werkzeug',
        'jsonschema',
        'ipaddr >= 2.2.0',
        'passlib',
        'psycopg2 >= 2.7.0',
        'reportlab',
        'simplejson',
        'wrapt',
    ],
    dependency_links=[
        'git+git://github.com/lukasjuhrich/sqlalchemy_schemadisplay.git'
        '@master#egg=sqlalchemy-schemadisplay',
    ],
    extras_require={
        'SchemaDisplay': [
            'sqlalchemy-schemadisplay',
        ]
    },
    tests_require=[
        'factory-boy',
        'Flask-Testing',
        'fixture',
        'nose',
        'pydot',
    ],
    entry_points={
        'console_scripts': [
            'pycroft = scripts.server_run:main',
            'pycroft_ldap_sync = ldap_sync.__main__:main',
        ]
    },
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
)
