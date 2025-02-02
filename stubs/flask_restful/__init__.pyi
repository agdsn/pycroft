import typing as t
from _typeshed import Incomplete

from flask import Response
from flask.views import MethodView

def abort(http_status_code, **kwargs) -> None: ...

class Api:
    representations: Incomplete
    urls: Incomplete
    prefix: Incomplete
    default_mediatype: Incomplete
    decorators: Incomplete
    catch_all_404s: Incomplete
    serve_challenge_on_401: Incomplete
    url_part_order: Incomplete
    errors: Incomplete
    blueprint_setup: Incomplete
    endpoints: Incomplete
    resources: Incomplete
    app: Incomplete
    blueprint: Incomplete
    def __init__(self, app: Incomplete | None = ..., prefix: str = ..., default_mediatype: str = ..., decorators: Incomplete | None = ..., catch_all_404s: bool = ..., serve_challenge_on_401: bool = ..., url_part_order: str = ..., errors: Incomplete | None = ...) -> None: ...
    def init_app(self, app) -> None: ...
    def owns_endpoint(self, endpoint): ...
    def error_router(self, original_handler, e): ...
    def handle_error(self, e: Exception) -> Response: ...
    def mediatypes_method(self): ...
    def add_resource(self, resource, *urls, **kwargs) -> None: ...
    def resource(self, *urls, **kwargs): ...
    def output(self, resource): ...
    def url_for(self, resource, **values): ...
    def make_response(self, data, *args, **kwargs): ...
    def mediatypes(self): ...
    def representation(self, mediatype): ...
    def unauthorized(self, response): ...

class Resource(MethodView):
    representations: Incomplete
    method_decorators: Incomplete
    @t.override
    def dispatch_request(self, *args, **kwargs): ...

def marshal(data, fields, envelope: Incomplete | None = ...): ...

class marshal_with:
    fields: Incomplete
    envelope: Incomplete
    def __init__(self, fields, envelope: Incomplete | None = ...) -> None: ...
    def __call__(self, f): ...

class marshal_with_field:
    field: Incomplete
    def __init__(self, field) -> None: ...
    def __call__(self, f): ...
