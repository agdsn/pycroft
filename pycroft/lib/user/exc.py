import typing as t

from ..exc import PycroftLibException


class HostAliasExists(ValueError):
    pass


class LoginTakenException(PycroftLibException):
    @t.override
    def __init__(  # ty: ignore[invalid-method-override]
        self, login: str | None = None, *args: object
    ) -> None:
        msg = "Login already taken" if not login else f"Login {login!r} already taken"
        super().__init__(msg)


class EmailTakenException(PycroftLibException):
    @t.override
    def __init__(self, *args: object) -> None:
        super().__init__(*args if args else ("E-Mail address already in use",))


class UserExistsInRoomException(PycroftLibException):
    @t.override
    def __init__(self, *args: object) -> None:
        super().__init__(
            *args if args else ("A user with a similar name already lives in this room",)
        )


class UserExistsException(PycroftLibException):
    @t.override
    def __init__(self, *args: object) -> None:
        super().__init__(*args if args else ("This user already exists",))


class NoTenancyForRoomException(PycroftLibException):
    @t.override
    def __init__(self, *args: object) -> None:
        super().__init__(*args if args else ("This user has no tenancy in that room",))


class MoveInDateInvalidException(PycroftLibException):
    @t.override
    def __init__(self, *args: object) -> None:
        super().__init__(
            *args
            if args
            else (
                "The move-in date is invalid (in the past or more than 6 months in the future)",
            )
        )
