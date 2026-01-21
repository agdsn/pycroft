import typing as t

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import IntegerIdModel
from .type_aliases import datetime_tz, str50

type JSON = dict[str, JSON] | list[JSON] | str | float | bool | None


@t.final
class ScrubLog(IntegerIdModel):
    executed_at: Mapped[datetime_tz] = mapped_column(server_default=func.current_timestamp(), index=True)

    scrubber: Mapped[str50] = mapped_column(index=True)
    info: Mapped[JSON] = mapped_column(JSONB, index=True)
