from flask import url_for

from pycroft import config
from pycroft.model import session
from pycroft.model.user import User
from pycroft.model.facilities import Room
from pycroft.model.webstorage import WebStorage
from tests.factories import UserWithHostFactory
from tests.fixtures import permissions
from tests.fixtures.dummy import user as dummy_user_fixtures, facilities
from . import UserFrontendTestBase, LegacyUserFrontendTestBase


class UserViewingPagesTestCase(UserFrontendTestBase):
    def test_user_overview_access(self):
        self.assert200(self.client.get(url_for('user.overview')))

    def test_user_viewing_himself(self):
        user_id = self.admin.id
        self.assert200(self.client.get(url_for('user.user_show', user_id=user_id)))

    def test_user_search_access(self):
        self.assert200(self.client.get(url_for('user.search')))


class UserBlockingTestCase(LegacyUserFrontendTestBase):
    def setUp(self):
        super().setUp()
        username = permissions.UserData.user3_user.login
        self.test_user_id = User.q.filter_by(login=username).one().id

    def test_blocking_and_unblocking_works(self):
        user_show_endpoint = url_for("user.user_show", user_id=self.test_user_id)
        response = self.client.get(user_show_endpoint)
        self.assert200(response)

        response = self.client.post(url_for("user.suspend", user_id=self.test_user_id),
                                    data={'ends_at-unlimited': 'y',
                                          'reason': 'Ist doof'})
        self.assertRedirects(response, user_show_endpoint)
        self.assert_message_flashed("Nutzer gesperrt", 'success')

        response = self.client.post(url_for("user.unblock", user_id=self.test_user_id))
        self.assertRedirects(response, user_show_endpoint)
        self.assert_message_flashed("Nutzer entsperrt", 'success')

    def test_unblocked_user_cannot_be_unblocked(self):
        response = self.client.post(url_for("user.unblock", user_id=self.test_user_id))
        self.assert404(response)
        self.assert_message_substr_flashed("ist nicht gesperrt!", category='error')


class UserMovingOutTestCase(LegacyUserFrontendTestBase):
    def setUp(self):
        super().setUp()
        username = permissions.UserData.user3_user.login
        self.user = User.q.filter_by(login=username).one()

    def test_user_cannot_be_moved_back_in(self):
        # attempt to move the user back in
        endpoint = url_for('user.move_in', user_id=self.user.id)
        response = self.client.post(endpoint, data={
            # Will be serialized to str implicitly
            'building': self.user.room.building.id,
            'level': self.user.room.level,
            'room_number': self.user.room.number,
            'mac': "00:de:ad:be:ef:00",
            'birthday': "1990-01-01"
        })
        self.assert_404(response)
        self.assert_message_flashed("Nutzer {} ist nicht ausgezogen!"
                                    .format(self.user.id), category='error')

    def test_user_moved_out_correctly(self):
        endpoint = url_for('user.move_out', user_id=self.user.id)
        response = self.client.post(endpoint)
        self.assert_redirects(response, url_for('user.user_show', user_id=self.user.id))
        self.assertMessageFlashed("Nutzer wurde ausgezogen", 'success')
        # TODO: Test whether everything has been done on the library side!


class UserMovedOutTestCase(LegacyUserFrontendTestBase):
    def setUp(self):
        super().setUp()
        # Taking the dummy user because the one from the `permission`
        # fixtures is member in `config.member_group`
        username = dummy_user_fixtures.UserData.dummy.login
        self.user = User.q.filter_by(login=username).one()

    def test_user_cannot_be_moved_out(self):
        self.user.room = None
        endpoint = url_for('user.move_out', user_id=self.user.id)
        response = self.client.post(endpoint, data={'comment': "Ist doof"})
        self.assert_404(response)
        self.assert_message_flashed("Nutzer {} ist aktuell nirgends eingezogen!"
                                    .format(self.user.id), category='error')

    def test_user_can_be_moved_back_in(self):
        # This test will fail due to unusable fixtures.  I recommend
        # against trying to fix them (they are “only” missing a
        # default traffic group for a building), because I tried that
        # and it takes far too long and far too much code duplication
        # that we shuold wait until somebody implements usable
        # factories.

        # user_id = self.user.id
        # endpoint = url_for('user.move_back_in', user_id=user_id)
        # # Pick a room, any room
        # room = Room.q.filter_by(inhabitable=True).limit(1).one()
        # response = self.client.post(endpoint, data={
        #     # Will be serialized to str implicitly
        #     'building': room.building.id,
        #     'level': room.level,
        #     'room_number': room.number,
        #     'mac': "00:de:ad:be:ef:00",
        # })
        # self.assert_redirects(response, url_for('user.user_show', user_id=user_id))
        # self.assert_message_flashed("Nutzer wurde wieder eingezogen", category='success')
        pass

    def test_static_datasheet(self):
        endpoint = url_for('user.static_datasheet', user_id=self.user.id)
        response = self.client.get(endpoint)
        self.assertTrue(response.data.startswith(b"%PDF"))
        self.assert200(response)
        self.assertEqual(response.headers.get('Content-Type'), "application/pdf")
        self.assertEqual(response.headers.get('Content-Disposition'),
                         "inline; filename=user_sheet_plain_{}.pdf".format(self.user.id))

    def test_password_reset(self):
        endpoint = url_for('user.reset_password', user_id=self.user.id)
        response = self.client.post(endpoint)
        self.assert_message_substr_flashed("Passwort erfolgreich zurückgesetzt.",
                                           category='success')
        # access user_sheet
        response = self.client.get(url_for('user.user_sheet'))
        self.assertEqual(WebStorage.q.count(), 1)
        self.assert200(response)
        self.assertEqual(response.headers.get('Content-Type'), "application/pdf")
        self.assertEqual(response.headers.get('Content-Disposition'),
                         "inline; filename=user_sheet.pdf")
        self.assertTrue(response.data.startswith(b"%PDF"))


class NewUserDatasheetTest(UserFrontendTestBase):
    def assert_user_moved_in(self, response):
        newest_user = User.q.order_by(User.id.desc()).first()
        self.assertRedirects(response, url_for('user.user_show', user_id=newest_user.id))
        self.assert_message_substr_flashed("Benutzer angelegt.", category='success')

    def test_user_create_data_sheet(self):
        response = self.client.post(url_for('user.create'), data={
            'name': "Test User",
            'building': self.room.building.id,
            'level': self.room.level,
            'room_number': self.room.number,
            'login': "testuser",
            'mac': "70:de:ad:be:ef:07",
            'birthdate': "1990-01-01",
            'email': "",
            'property_group': config.member_group.id
        })
        self.assert_user_moved_in(response)
        response = self.client.get(url_for('user.user_sheet'))
        self.assertEqual(WebStorage.q.count(), 1)
        self.assert200(response)
        self.assertEqual(response.headers.get('Content-Type'), "application/pdf")
        self.assertEqual(response.headers.get('Content-Disposition'),
                         "inline; filename=user_sheet.pdf")
        self.assertTrue(response.data.startswith(b"%PDF"))

    def test_user_host_annexation(self):
        mac = "00:de:ad:be:ef:00"
        other_user = UserWithHostFactory(host__interface__mac=mac)
        session.session.commit()
        self.assertEqual(len(other_user.hosts), 1)

        move_in_formdata = {
            'name': "Test User",
            'building': str(self.room.building.id),
            'level': str(self.room.level),
            'room_number': self.room.number,
            'login': "testuser",
            'mac': mac,
            'email': "",
            'birthdate': "1990-01-01",
            'property_group': config.member_group.id
        }
        response = self.client.post(url_for('user.create'), data=move_in_formdata)
        self.assert200(response)
        self.assertIsNone(response.location)

        move_in_formdata.update(annex="y")
        response = self.client.post(url_for('user.create'), data=move_in_formdata)
        self.assert_user_moved_in(response)
