# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import typing as t
from collections import OrderedDict

from flask import Flask
from flask.globals import request_ctx

class LinkedScript(t.NamedTuple):
    url: str
    mime_type: str


class PageResources(t.NamedTuple):
    script_files: OrderedDict[str, LinkedScript]
    ready_scripts: list[str]
    stylesheet_files: OrderedDict[str, str]


class PageResourceRegistry:
    """Register resources like script files for later inclusion in pages."""

    @property
    def page_resources(self) -> PageResources:
        """Page resources are attached to Flask's current request context."""
        ctx = request_ctx
        if hasattr(ctx, "page_resources"):
            assert isinstance(ctx.page_resources, PageResources)
            return ctx.page_resources

        res = PageResources(OrderedDict(), [], OrderedDict())
        ctx.page_resources = res  # type: ignore[attr-defined]
        return res

    @property
    def script_files(self) -> OrderedDict[str, LinkedScript]:
        return self.page_resources.script_files

    @property
    def ready_scripts(self) -> list[str]:
        return self.page_resources.ready_scripts

    @property
    def stylesheet_files(self) -> OrderedDict[str, str]:
        return self.page_resources.stylesheet_files

    def link_stylesheet(self, url: str) -> None:
        """Link a stylesheet file using a URL"""
        self.stylesheet_files.setdefault(url, url)

    def link_script(self, url: str, mime_type: str = "text/javascript") -> None:
        """
        Link a script file using a URL.

        A particular URL will only be included once. Scripts are linked in the
        order they were first added.
        """
        self.script_files.setdefault(url, LinkedScript(url, mime_type))

    def append_ready_script(self, script: str) -> None:
        """
        Register a script as jQuery onReady handler.

        The scripts will be wrapped in a closure to prevent name clashes between
        variables.
        """
        self.ready_scripts.append(script)

    def init_app(self, app: Flask) -> None:
        app.context_processor(lambda: {"page_resources": self})


page_resources = PageResourceRegistry()
