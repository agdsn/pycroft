# -*- coding: utf-8 -*-
from flask import url_for
from tests import FrontendDataTestBase
from tests.frontend.fixtures.dormitory_fixtures import DormitoryData, RoomData, UserData

__author__ = 'Florian Österreich'


class Test_010_Dormitory(FrontendDataTestBase):
    datasets = [DormitoryData, RoomData, UserData]

    def setUp(self):
        self.login = "test"
        self.password = "password"
        super(Test_010_Dormitory, self).setUp()

    def test_0010_list_dormitories(self):
        self.assert_template_get_request("/dormitories/",
                                         "dormitories/overview.html")

    def test_0020_show_dormitory(self):
        self.assert_template_get_request(
            "/dormitories/show/%s" % DormitoryData.dummy_house1.id,
            "dormitories/dormitory_show.html")

    def test_0030_create_dormitory(self):
        self.assert_template_get_request("/dormitories/create",
                                         "dormitories/dormitory_create.html")

    def test_0040_show_room(self):
        self.assert_template_get_request(
            "/dormitories/room/show/%s" % RoomData.dummy_room1.id,
            "dormitories/room_show.html")

    def test_0050_create_room(self):
        self.assert_template_get_request(
            "/dormitories/room/create", "dormitories/dormitory_create.html")

    def test_0060_delete_room(self):
        self.assertRedirects(self.client.get(
            "/dormitories/room/delete/%s" % RoomData.dummy_room2.id),
            url_for("dormitories.overview"))

    def test_0070_dormitory_levels(self):
        self.assert_template_get_request(
            "/dormitories/levels/%s" % DormitoryData.dummy_house1.id,
            "dormitories/levels.html")

    def test_0080_dormitory_level_rooms(self):
        self.assert_template_get_request(
            "/dormitories/levels/%s/rooms/%s" % (
            DormitoryData.dummy_house1.id, RoomData.dummy_room1.level),
            "dormitories/rooms.html")
