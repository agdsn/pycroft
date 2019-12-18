from pycroft.helpers import AutoNumber


class MailEvent(AutoNumber):
    MEMBER_MOVED_OUT = ()
    MEMBER_MOVED_IN = ()
    MEMBER_MOVED = ()
    MEMBER_MOVE_OUT_SCHEDULED = ()
    USER_PAYMENT_IN_DEFAULT = ()
    USER_PAYMENT_IN_DEFAULT_BLOCKED = ()
    USER_BLOCKED = ()
    USER_PAYMENT_MATCHED_AUTO = ()
    USER_PAYMENT_MATCHED_MANUALLY = ()
