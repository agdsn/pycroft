#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import pytest

from ldap_sync.conversion import db_user_to_record
from ldap_sync.types import DN


class TestRecordFromOrm:
    @pytest.fixture(scope='class')
    def attrs(self):
        class complete_user:
            name = 'foo bar shizzle'
            login = 'shizzle'
            email = 'shizzle@agdsn.de'
            email_forwarded = True

            class unix_account:
                uid = 10006
                gid = 100
                home_directory = '/home/test'
                login_shell = '/bin/bash'
            passwd_hash = 'somehash'

        return db_user_to_record(complete_user, base_dn=DN("o=test")).attrs

    def test_uid_correct(self, attrs):
        assert attrs['uid'] == ['shizzle']

    def test_uidNumber_correct(self, attrs):
        assert attrs['uidNumber'] == [10006]

    def test_gidNumber_correct(self, attrs):
        assert attrs['gidNumber'] == [100]

    def test_homeDirectory_correct(self, attrs):
        assert attrs['homeDirectory'] == ['/home/test']

    def test_userPassword_correct(self, attrs):
        assert attrs['userPassword'] == ['somehash']

    def test_gecos_correct(self, attrs):
        assert attrs['gecos'] == ['foo bar shizzle']

    def test_cn_correct(self, attrs):
        assert attrs['cn'] == ['foo bar shizzle']

    def test_sn_correct(self, attrs):
        assert attrs['sn'] == ['foo bar shizzle']

    def test_mail_correct(self, attrs):
        assert attrs['mail'] == ['shizzle@agdsn.de']
