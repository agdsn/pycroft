# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import typing as t
from typing import NoReturn

from flask import Blueprint, abort
from werkzeug import Response
from werkzeug.utils import redirect


class NamedCallable(t.Protocol):
    __name__: str

    def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any: ...


def bake_endpoint(blueprint: Blueprint, fn: NamedCallable) -> str:
    return f"{blueprint.name}.{fn.__name__}"


def redirect_or_404(redirect_url: str | None) -> Response | NoReturn:
    """Helper function to return a redirect or abort.

    **The return vaue must be used!**
    """
    if redirect_url:
        return redirect(redirect_url)
    abort(404)
