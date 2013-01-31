# -*- coding: utf-8 -*-

__author__ = 'florian'

from tests import FixtureDataTestBase
from pycroft.lib import user as UserHelper, user_config
from tests.helpers.fixtures.user_fixtures import DormitoryData, FinanceAccountData, \
    RoomData, UserData, UserNetDeviceData, UserHostData, IpData, VLanData, SubnetData, \
    PatchPortData, SemesterData, TrafficGroupData, PropertyGroupData, \
    PropertyData
from pycroft.model import user, dormitory, port, session, logging, finance, \
    property, host_alias, host
from datetime import datetime

class Test_010_User_Move(FixtureDataTestBase):
    datasets = [DormitoryData, RoomData, UserData, UserNetDeviceData, UserHostData,
                IpData, VLanData, SubnetData, PatchPortData]

    def setUp(self):
        super(Test_010_User_Move, self).setUp()
        self.user = user.User.q.get(1)
        self.processing_user = user.User.q.get(2)
        self.old_room = dormitory.Room.q.get(1)
        self.new_room_other_dormitory = dormitory.Room.q.get(2)
        self.new_room_same_dormitory = dormitory.Room.q.get(3)
        self.new_patch_port = port.PatchPort.q.get(2)

    def tearDown(self):
        #TODO don't delete all log entries but the user log entries
        logging.LogEntry.q.delete()
        session.session.commit()
        super(Test_010_User_Move, self).tearDown()

    def test_0010_moves_into_same_room(self):
        self.assertRaises(AssertionError, UserHelper.move,
            self.user, self.old_room.dormitory, self.old_room.level,
            self.old_room.number, self.processing_user)

    def test_0020_moves_into_other_dormitory(self):
        UserHelper.move(self.user, self.new_room_other_dormitory.dormitory,
            self.new_room_other_dormitory.level,
            self.new_room_other_dormitory.number, self.processing_user)
        self.assertEqual(self.user.room, self.new_room_other_dormitory)
        self.assertEqual(self.user.user_host.room, self.new_room_other_dormitory)
        #TODO test for changing ip


class Test_020_User_Move_In(FixtureDataTestBase):
    datasets = [DormitoryData, FinanceAccountData, RoomData, UserData,
                UserNetDeviceData, UserHostData, IpData, VLanData, SubnetData,
                PatchPortData, SemesterData, TrafficGroupData,
                PropertyGroupData, PropertyData]

    def setUp(self):
        super(Test_020_User_Move_In, self).setUp()
        self.processing_user = user.User.q.get(1)


    def tearDown(self):
        #TODO don't delete all log entries but the user log entries
        logging.LogEntry.q.delete()
        finance.Transaction.q.delete()
        session.session.commit()
        super(Test_020_User_Move_In, self).tearDown()

    def test_0010_move_in(self):
        def get_initial_groups():
            initial_groups = []
            for group in user_config.initial_groups:
                initial_groups.append(property.Group.q.filter(
                    property.Group.name == group["group_name"]
                ).one())
            return initial_groups

        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_dormitory = dormitory.Dormitory.q.first()
        test_hostname = "hans"
        test_mac = "12:11:11:11:11:11"

        new_user = UserHelper.moves_in(test_name,
            test_login, test_email, test_dormitory,
            1,
            "1",
            test_hostname,
            test_mac,
            finance.Semester.q.first(),
            self.processing_user)

        self.assertEqual(new_user.name, test_name)
        self.assertEqual(new_user.login, test_login)
        self.assertEqual(new_user.email, test_email)
        self.assertEqual(new_user.room.dormitory, test_dormitory)
        self.assertEqual(new_user.room.number, "1")
        self.assertEqual(new_user.room.level, 1)
        self.assertEqual(new_user.user_host.user_net_device.mac, test_mac)

        user_host = host.UserHost.q.filter_by(user=new_user).one()
        user_net_device = host.UserNetDevice.q.filter_by(host=user_host).one()
        self.assertEqual(user_net_device.mac, test_mac)
        user_cnamerecord = host_alias.CNameRecord.q.filter_by(host=user_host).one()
        self.assertEqual(user_cnamerecord.name, test_hostname)
        user_arecord = host_alias.ARecord.q.filter_by(host=user_host).one()
        self.assertEqual(user_cnamerecord.alias_for, user_arecord)

        #checks the initial group memberhsips
        user_groups = new_user.active_property_groups + new_user.active_traffic_groups
        for group in get_initial_groups():
            self.assertIn(group, user_groups)

        self.assertEqual(UserHelper.has_internet(new_user), True)
        user_account = finance.FinanceAccount.q.filter(
                finance.FinanceAccount.user==new_user
            ).filter(
                finance.FinanceAccount.name==u"Nutzerid: %d" % new_user.id
            ).one()
        splits = finance.Split.q.filter(
                finance.Split.account_id == user_account.id
            ).all()
        account_sum = sum([split.amount for split in splits])
        self.assertEqual(account_sum,4000)

class Test_0030_User_Move_Out(FixtureDataTestBase):
    datasets = [IpData, PatchPortData, SemesterData, TrafficGroupData,
                PropertyGroupData, FinanceAccountData]

    def setUp(self):
        super(Test_0030_User_Move_Out, self).setUp()
        self.processing_user = user.User.q.get(1)

    def tearDown(self):
        logging.LogEntry.q.delete()
        finance.Transaction.q.delete()
        session.session.commit()
        super(Test_0030_User_Move_Out, self).tearDown()


    def test_0030_move_out(self):
        def get_initial_groups():
            initial_groups = []
            for group in user_config.initial_groups:
                initial_groups.append(property.Group.q.filter(
                    property.Group.name == group["group_name"]
                ).one())
            return initial_groups

        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_dormitory = dormitory.Dormitory.q.first()
        test_mac = "12:11:11:11:11:11"

        new_user = UserHelper.moves_in(test_name,
            test_login, test_email, test_dormitory,
            1,
            "1",
            None,
            test_mac,
            finance.Semester.q.first(),
            self.processing_user)

        out_time = datetime.now()

        UserHelper.move_out(new_user, out_time, "", self.processing_user)

        # check end_date of moved out user
        for membership in new_user.memberships:
            if membership.end_date >= out_time:
                self.assertEquals(membership.end_date, out_time)

        # check if users finance account still exists
        user_account = finance.FinanceAccount.q.filter(
            finance.FinanceAccount.user==new_user
        ).filter(
            finance.FinanceAccount.name==u"Nutzerid: %d" % new_user.id
        ).one()

class Test_040_User_Edit_Name(FixtureDataTestBase):
    datasets = [RoomData, DormitoryData, UserData]

    def setUp(self):
        super(Test_040_User_Edit_Name, self).setUp()
        self.user = user.User.q.get(2)

    def tearDown(self):
        logging.LogEntry.q.delete()
        session.session.commit()
        super(Test_040_User_Edit_Name, self).tearDown()

    def test_0010_correct_new_name(self):
        print self.user.name
        print self.user.id

        UserHelper.edit_name(self.user, "toller neuer Name", self.user)

        self.assertEqual(self.user.name, "toller neuer Name")

    def test_0020_name_zero_length(self):
        old_name = self.user.name

        UserHelper.edit_name(self.user, "", self.user)

        self.assertEqual(self.user.name, old_name)


class Test_050_User_Edit_Email(FixtureDataTestBase):
    datasets = [RoomData, DormitoryData, UserData]

    def setUp(self):
        super(Test_050_User_Edit_Email, self).setUp()
        self.user = user.User.q.get(2)

    def tearDown(self):
        logging.LogEntry.q.delete()
        session.session.commit()
        super(Test_050_User_Edit_Email, self).tearDown()

    def test_0010_correct_new_email(self):
        UserHelper.edit_email(self.user, "sebastian@schrader.de", self.user)

        self.assertEqual(self.user.email, "sebastian@schrader.de")

    def test_0020_email_zero_length(self):
        old_email = self.user.email

        UserHelper.edit_email(self.user, "", self.user)

        self.assertEqual(self.user.email, old_email)


class Test_060_User_Balance(FixtureDataTestBase):
    datasets = [RoomData, DormitoryData, UserData, FinanceAccountData,
                SemesterData]

    def _has_positive_balance(self):
        return UserHelper.has_positive_balance(self.user)

    def _has_balance_of_at_least(self, amount):
        return UserHelper.has_balance_of_at_least(self.user, amount)

    def _add_amount(self, amount):
        transaction = finance.Transaction(message=self.msg,
                                          semester=self.semester)
        user_split = finance.Split(amount=amount,
                                   account=self.user.finance_account,
                                   transaction=transaction)
        other_split = finance.Split(amount=-amount,
                                    account=self.account,
                                    transaction=transaction)
        session.session.add(transaction)
        session.session.add(user_split)
        session.session.add(other_split)

    def setUp(self):
        super(Test_060_User_Balance, self).setUp()
        self.user = user.User.q.filter(user.User.login == 'admin').first()
        self.account = finance.FinanceAccount.q.first()
        self.semester = finance.Semester.q.first()
        self.msg = repr(self) + repr(self.semester)

    def tearDown(self):
        finance.Transaction.q.filter(
            finance.Transaction.message == self.msg
        ).delete()
        session.session.commit()
        super(Test_060_User_Balance, self).tearDown()

    def test_0010_has_positive_balance(self):
        self.assertIsNotNone(self.user.finance_account)
        self.assertTrue(self._has_positive_balance())
        self.assertTrue(self._has_balance_of_at_least(0))
        self.assertTrue(self._has_balance_of_at_least(-23))
        self.assertFalse(self._has_balance_of_at_least(1))

    def test_0020_user_without_finance_account(self):
        u = user.User.q.filter(user.User.login == 'test').first()
        self.assertIsNone(u.finance_account)
        self.assertTrue(UserHelper.has_positive_balance(u))
        self.assertTrue(UserHelper.has_balance_of_at_least(u, 0))
        self.assertTrue(UserHelper.has_balance_of_at_least(u, -23))
        self.assertFalse(UserHelper.has_balance_of_at_least(u, 1))

    def test_0030_has_balance_of_over_nine_thousand(self):
        self.assertFalse(self._has_balance_of_at_least(9001))
        self.assertTrue(self._has_positive_balance())
        self._add_amount(9001)
        self.assertTrue(self._has_balance_of_at_least(9001))
        self.assertTrue(self._has_positive_balance())
        self._add_amount(-1)
        self.assertFalse(self._has_balance_of_at_least(9001))
        self.assertTrue(self._has_balance_of_at_least(9000))
        self.assertTrue(self._has_balance_of_at_least(-1337))
        self.assertTrue(self._has_positive_balance())
