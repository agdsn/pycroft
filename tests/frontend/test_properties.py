from flask import url_for

from pycroft.model._all import PropertyGroup
from tests import FrontendWithAdminTestBase


class PropertiesFrontendTestCase(FrontendWithAdminTestBase):
    def test_property_gets_added(self):
        url = url_for('properties.property_group_create')
        group_name = "This is my first property group"
        # first time: a redirect
        response = self.assert_response_code(url, code=302, method='post',
                                             data={'name': group_name})
        self.assertEqual(response.location, url_for('properties.property_groups', _external=True))
        response = self.assert_response_code(response.location, code=200)

        content = response.data.decode('utf-8')
        # This actually should be `assert_flashed`
        self.assertIn(group_name, content)

        self.assertEqual(PropertyGroup.q.filter_by(name=group_name).count(), 1,
                         msg="Expected one property group of name '{}'".format(group_name))

