#  Copyright (c) 2021. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""
pycroft.model.interval_base
~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from sqlalchemy import Column, func, CheckConstraint, and_, or_, null, literal
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import object_session, validates

from pycroft.helpers.interval import single, closed
from pycroft.model.types import DateTimeTz


class IntervalModel:
    import warnings
    warnings.warn('Use a column of type `TsTzRange` instead', DeprecationWarning)

    begins_at = Column(DateTimeTz, nullable=False, index=True,
                       server_default=func.current_timestamp())
    ends_at = Column(DateTimeTz, nullable=True, index=True)

    __table_args__ = (
        CheckConstraint("ends_at IS NULL OR begins_at <= ends_at"),
    )

    @hybrid_method
    def active(self, when=None):
        """
        Tests if overlaps with a given interval. If no interval is
        given, it tests if active right now.
        :param Interval when: interval to test
        :rtype: bool
        """
        if when is None:
            now = object_session(self).query(func.current_timestamp()).scalar()
            when = single(now)

        return when.overlaps(closed(self.begins_at, self.ends_at))

    @active.expression
    def active(cls, when=None):
        """
        Tests if overlaps with a given interval. If no interval is
        given, it tests if active right now.
        :param Interval when:
        :return:
        """
        if when is None:
            # use `current_timestamp()`
            return and_(
                or_(cls.begins_at == null(), cls.begins_at <= func.current_timestamp()),
                or_(cls.ends_at == null(), func.current_timestamp() <= cls.ends_at)
            ).label('active')

        return and_(
            or_(cls.begins_at == null(), literal(when.end) == null(),
                cls.begins_at <= literal(when.end)),
            or_(literal(when.begin) == null(), cls.ends_at == null(),
                literal(when.begin) <= cls.ends_at)
        ).label("active")

    @validates('ends_at')
    def validate_ends_at(self, _, value):
        if value is None:
            return value
        if self.begins_at is not None:
            assert value >= self.begins_at,\
                "begins_at must be before ends_at"
        return value

    @validates('begins_at')
    def validate_begins_at(self, _, value):
        assert value is not None, "begins_at cannot be None"

        if self.ends_at is not None:
            assert value <= self.ends_at,\
                "begins_at must be before ends_at"
        return value

    def disable(self, ends_at=None):
        if ends_at is None:
            ends_at = object_session(self).query(func.current_timestamp()).scalar()

        if self.begins_at is not None and self.begins_at > ends_at:
            self.ends_at = self.begins_at
        else:
            self.ends_at = ends_at
