# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'jan'

from fixture.style import TrimmedNameStyle
from fixture import DataSet, SQLAlchemyFixture, DataTestCase
from pycroft.model import session, _all
from pycroft.model import drop_db_model, create_db_model

from tests.unittest26_compat import OldPythonTestCase


def make_fixture():
    """A helper to create a database fixture.
    """
    fixture = SQLAlchemyFixture(
            env=_all,
            style=TrimmedNameStyle(suffix="Data"),
            engine=session.session.get_engine() )
    return fixture


class FixtureDataTestBase(DataTestCase, OldPythonTestCase):
    """A TestCase baseclass that handles database fixtures.

    You only need to define a `datasets` class member with a list of
    the fixture DataSets. The type of the fixture element will be taken
    from the name of the DataSet class. It needs "Data" as suffic. So if
    you want to provide fixtures for the User model the name of the DataSet
    has to be "UserData". See also test_property.py for an example.

    If you overwrite the `tearDown` or `setUpClass` methods don't forget
    to call the ones in the superclass.
    """

    @classmethod
    def setUpClass(cls):
        session.reinit_session("sqlite://")
        drop_db_model()
        create_db_model()
        cls.fixture = make_fixture()

    def tearDown(self):
        super(FixtureDataTestBase, self).tearDown()
        session.session.remove()
