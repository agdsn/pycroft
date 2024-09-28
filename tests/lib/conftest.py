#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import pytest
from sqlalchemy import func
from sqlalchemy.future import select

from pycroft.model import _all as m
from pycroft.lib.mail import MailConfig, _config_var
from tests import factories


@pytest.fixture(scope='module')
def utcnow(module_session):
    return module_session.scalar(select(func.current_timestamp()))


@pytest.fixture(scope="module")
def processor(module_session) -> m.User:
    return factories.UserFactory.create()


@pytest.fixture(scope="module")
def config(module_session) -> m.Config:
    return factories.ConfigFactory.create()


@pytest.fixture(scope="module", autouse=True)
def with_mail_config():
    token = _config_var.set(
        MailConfig(
            mail_envelope_from="noreply@agdsn.de",
            mail_from="noreply@agdsn.de",
            mail_reply_to="support@agdsn.de",
            smtp_host="agdsn.de",
            smtp_user="pycroft",
            smtp_password="password",
        )
    )
    yield
    _config_var.reset(token)
