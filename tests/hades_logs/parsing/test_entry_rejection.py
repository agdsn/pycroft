from hades_logs import RadiusLogEntry


def assert_acceptance_from_reply(reply, should_accept=False):
    entry = RadiusLogEntry(mac=None, reply=reply, groups=None, raw_attributes=None, timestamp=None)
    if should_accept:
        assert entry.accepted
        assert entry
    else:
        assert not entry.accepted
        assert not entry


def test_explicit_reject():
    assert_acceptance_from_reply("Access-Reject")


def test_implicit_reject():
    assert_acceptance_from_reply("SomeBogusValue")


def test_accept():
    assert_acceptance_from_reply("Access-Accept", should_accept=True)
