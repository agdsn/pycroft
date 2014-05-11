from collections import namedtuple, OrderedDict
from flask import _request_ctx_stack

__author__ = 'shreyder'


LinkedScript = namedtuple("LinkedScript", ("url", "mime_type"))


class PageResourceRegistry(object):
    """Register resources like script files for later inclusion in pages."""

    @property
    def page_resources(self):
        """Page resources are attached to Flask's current request context."""
        ctx = _request_ctx_stack.top
        if not hasattr(ctx, "page_resources"):
            ctx.page_resources = namedtuple(
                "PageResources", ("script_files", "ready_scripts")
            )(OrderedDict(), list())
        return ctx.page_resources

    def link_script(self, url, mime_type="text/javascript"):
        """
        Link a script file using a URL.

        A particular URL will only be included once. Scripts are linked in the
        order they were added.
        """
        print("linked {}".format(url))
        self.page_resources.script_files[url] = LinkedScript(url, mime_type)

    def ready_script(self, script):
        """
        Register a script as jQuery onReady handler.

        The scripts will be wrapped in closure to prevent name clashes between
        variables.
        """
        self.page_resources.ready_scripts.append(script)

    def init_app(self, app):
        app.context_processor(lambda: {"page_resources": self.page_resources})


page_resources = PageResourceRegistry()
