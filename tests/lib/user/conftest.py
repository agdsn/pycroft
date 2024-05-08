import pytest

from pycroft.lib.mail import Mail


@pytest.fixture
def mail_capture(monkeypatch) -> list[Mail]:
    mails_captured = []

    class TaskStub:
        @staticmethod
        def delay(mails):
            assert all(isinstance(m, Mail) for m in mails), "didn't get an instance of Mail()"
            mails_captured.extend(mails)

    monkeypatch.setattr("pycroft.lib.user.send_mails_async", TaskStub)
    yield mails_captured
