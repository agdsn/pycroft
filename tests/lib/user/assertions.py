from pycroft.helpers.i18n import localized


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
