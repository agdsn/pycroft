# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import typing as t

from factory.alchemy import SQLAlchemyModelFactory as Factory

from pycroft.model.session import session


class BaseFactory[T](Factory):
    class Meta:
        sqlalchemy_session = session
        sqlalchemy_session_persistence = "flush"

    if t.TYPE_CHECKING:

        def __new__(cls, **kwargs: t.Any) -> T: ...

        @classmethod
        def create(cls, **kwargs: t.Any) -> T: ...

        @classmethod
        def build(cls, **kwargs: t.Any) -> T: ...


def copy_factory(factory: type[Factory], orig):
    return factory.build(
        **{
            field_name: getattr(orig, field_name)
            for field_name in factory._meta.pre_declarations
            if hasattr(orig, field_name)
        }
    )
