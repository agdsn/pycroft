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


class TrafficGroupTestCase(FrontendWithAdminTestBase):
    group_name = "Test Trafficgruppe"

    def assert_traffic_group_can_be_added(self, data):
        """Assert whether a traffic group can be added

        :param dict data: the POST data to be transmitted
        """
        group_name = data['name']
        endpoint = url_for('properties.traffic_group_create')
        response = self.client.post(endpoint, data=data)
        target_url = url_for('properties.traffic_groups')
        self.assert_redirects(response, target_url)
        response = self.client.get(target_url)
        self.assert200(response)
        self.assert_message_substr_flashed(group_name, category='success')

    def assert_form_validation_error(self, data):
        """Assert whether traffic group creation fails due to form
        validation

        :param dict data: the POST data to be transmitted
        """
        endpoint = url_for('properties.traffic_group_create')
        response = self.client.post(endpoint, data=data)
        # HTTP 200 is a sufficient indicator for a validation failure.
        # Success would result in a redirect.
        self.assert200(response)


    def test_trafficgroup_can_be_added(self):
        data = {
            'name': self.group_name,
            'credit_interval': "0 years 0 mons 1 days 0 hours 0 mins 0 secs",
            'credit_amount': "3",
            'credit_limit': "63",
            'initial_credit': "21",
        }
        self.assert_traffic_group_can_be_added(data)

    def test_bad_interval_formats(self):
        bad_intervals = [
            # our validation is quite strict
            "0 mons",
            "0 years 0 mons 0 days 0 hours 0 mins",
            "0 years 0 mons 0 days 0 hours 0 mins 0 secs",
            "0 years 1 months 0 days 0 hours 0 mins 0 secs",
            "0 years 1 days 0 mons 0 hours 0 mins 0 secs",
            "0 years zero mons 0 days 0 hours 0 mins 0 secs",
        ]
        for interval in bad_intervals:
            with self.subTest(interval=interval):
                data = {
                    'name': self.group_name,
                    'credit_interval': interval,
                    'credit_amount': "3",
                    'credit_limit': "63",
                    'initial_credit': "21",
                }
                self.assert_form_validation_error(data)
