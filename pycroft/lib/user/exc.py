import typing as t

from ..exc import PycroftLibException


class HostAliasExists(ValueError):
    pass


class LoginTakenException(PycroftLibException):
    @t.override
    def __init__(self, login: str | None = None) -> None:
        msg = "Login already taken" if not login else f"Login {login!r} already taken"
        super().__init__(msg)


class EmailTakenException(PycroftLibException):
    @t.override
    def __init__(self) -> None:
        super().__init__("E-Mail address already in use")


class UserExistsInRoomException(PycroftLibException):
    @t.override
    def __init__(self) -> None:
        super().__init__("A user with a similar name already lives in this room")


class UserExistsException(PycroftLibException):
    @t.override
    def __init__(self) -> None:
        super().__init__("This user already exists")


class NoTenancyForRoomException(PycroftLibException):
    @t.override
    def __init__(self) -> None:
        super().__init__("This user has no tenancy in that room")


class MoveInDateInvalidException(PycroftLibException):
    @t.override
    def __init__(self) -> None:
        super().__init__(
            "The move-in date is invalid (in the past or more than 6 months in the future)"
        )
