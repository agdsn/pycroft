from collections import namedtuple, OrderedDict
from flask import _request_ctx_stack


LinkedScript = namedtuple("LinkedScript", ("url", "mime_type"))
PageResources = namedtuple("PageResources", ("script_files", "ready_scripts"))


class PageResourceRegistry(object):
    """Register resources like script files for later inclusion in pages."""

    @property
    def page_resources(self):
        """Page resources are attached to Flask's current request context."""
        ctx = _request_ctx_stack.top
        if not hasattr(ctx, "page_resources"):
            ctx.page_resources = PageResources(OrderedDict(), list())
        return ctx.page_resources

    def link_script(self, url, mime_type="text/javascript"):
        """
        Link a script file using a URL.

        A particular URL will only be included once. Scripts are linked in the
        order they were first added.
        """
        self.page_resources.script_files[url] = LinkedScript(url, mime_type)

    def append_ready_script(self, script):
        """
        Register a script as jQuery onReady handler.

        The scripts will be wrapped in a closure to prevent name clashes between
        variables.
        """
        self.page_resources.ready_scripts.append(script)

    def init_app(self, app):
        app.context_processor(lambda: {"page_resources": self.page_resources})


page_resources = PageResourceRegistry()
