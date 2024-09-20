# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.user
~~~~~~~~~~~~~~~~

This module contains.

:copyright: (c) 2012 by AG DSN.
"""
import os


from pycroft.helpers.user import generate_random_str
from pycroft.lib.mail import (
    UserResetPasswordTemplate,
)
from pycroft.model.session import with_transaction
from pycroft.model.user import (
    User,
)

from .mail import user_send_mail


password_reset_url = os.getenv('PASSWORD_RESET_URL')


@with_transaction
def send_password_reset_mail(user: User) -> bool:
    user.password_reset_token = generate_random_str(64)

    if not password_reset_url:
        raise ValueError("No url specified in PASSWORD_RESET_URL")

    try:
        user_send_mail(user, UserResetPasswordTemplate(
                       password_reset_url=password_reset_url.format(user.password_reset_token)),
                       use_internal=False)
    except ValueError:
        user.password_reset_token = None
        return False

    return True
