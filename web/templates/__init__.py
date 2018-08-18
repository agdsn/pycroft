# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from collections import OrderedDict, namedtuple

from flask import _request_ctx_stack

LinkedScript = namedtuple("LinkedScript", ("url", "mime_type"))
PageResources = namedtuple("PageResources", ("script_files", "ready_scripts",
                                             "stylesheet_files"))


class PageResourceRegistry(object):
    """Register resources like script files for later inclusion in pages."""

    @property
    def page_resources(self):
        """Page resources are attached to Flask's current request context."""
        ctx = _request_ctx_stack.top
        if not hasattr(ctx, "page_resources"):
            ctx.page_resources = PageResources(OrderedDict(), list(),
                                               OrderedDict())
        return ctx.page_resources

    @property
    def script_files(self):
        return self.page_resources.script_files

    @property
    def ready_scripts(self):
        return self.page_resources.ready_scripts

    @property
    def stylesheet_files(self):
        return self.page_resources.stylesheet_files

    def link_stylesheet(self, url):
        """Link a stylesheet file using a URL"""
        self.stylesheet_files.setdefault(url, url)

    def link_script(self, url, mime_type="text/javascript"):
        """
        Link a script file using a URL.

        A particular URL will only be included once. Scripts are linked in the
        order they were first added.
        """
        self.script_files.setdefault(url, LinkedScript(url, mime_type))

    def append_ready_script(self, script):
        """
        Register a script as jQuery onReady handler.

        The scripts will be wrapped in a closure to prevent name clashes between
        variables.
        """
        self.ready_scripts.append(script)

    def init_app(self, app):
        app.context_processor(lambda: {"page_resources": self})


page_resources = PageResourceRegistry()
