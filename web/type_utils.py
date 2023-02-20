#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import typing as t

from werkzeug.exceptions import abort as abort_
from werkzeug.wrappers import BaseResponse


def abort(code: int | BaseResponse, *args: t.Any, **kwargs: t.Any) -> t.NoReturn:
    """Typed wrapper for werkzeug/flask's `abort` function."""
    # TODO remove once on flask v2
    return abort_(code, *args, **kwargs)
