import re
import typing as t

from pycroft.helpers.i18n import localized
from pycroft.lib.mail import Mail


def assert_account_name(account, expected_name):
    assert localized(account.name, {int: {'insert_commas': False}}) == expected_name


def assert_membership_groups(memberships, expected_groups):
    assert len(memberships) == len(expected_groups)
    assert {m.group for m in memberships} == set(expected_groups)


def assert_logmessage_startswith(logentry, expected_start: str):
    localized_message = localized(logentry.message)
    assert localized_message.startswith(
        expected_start
    ), f"Message {localized_message!r} does not start with {expected_start!r}"


def assert_mail_reasonable(mail: t.Any, subject_re: str | re.Pattern | None) -> Mail:
    assert "<a" not in mail.body_plain, "HTML anchor <a> found in mail's plain body"
    assert "<pre>" in mail.body_html, "No <pre> found in mail's HTML body"
    if subject_re:
        assert re.match(
            subject_re, mail.subject
        ), f"Mail's subject didn't contain the pattern {subject_re!r}: ({mail.subject=!r})"
