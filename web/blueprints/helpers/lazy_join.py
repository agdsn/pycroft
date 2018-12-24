from functools import wraps
from types import FunctionType
from typing import Generator, Callable, Iterable, overload


class LazyJoined:
    """A string that consists of multiple components"""
    _components: Iterable

    def __init__(self, components: Iterable, glue: str = ""):
        self.glue = glue
        self._components = components

    def __str__(self):
        return self.glue.join(str(c) for c in self._components)

    def __iter__(self):
        # TODO if glue, insert it every second time
        return iter(self._components)


DecoratedInType = Callable[..., (Generator[str, None, None])]
DecoratedOutType = Callable[..., LazyJoined]

@overload
def lazy_join(func_or_glue: DecoratedInType) -> DecoratedOutType:
    ...
@overload
def lazy_join(func_or_glue: str) -> Callable[[DecoratedInType], DecoratedOutType]:
    ...
def lazy_join(func_or_glue):
    if type(func_or_glue) == FunctionType:
        # Return the wrapped function
        return LazyJoinDecorator()(func=func_or_glue)
    # Return the decorator
    return LazyJoinDecorator(glue=func_or_glue)


class LazyJoinDecorator:
    def __init__(self, glue: str = ""):
        self.glue = glue

    def __call__(self, func: DecoratedInType) -> DecoratedOutType:
        @wraps(func)
        def wrapped(*a, **kw):
            return LazyJoined(func(*a, **kw), glue=self.glue)

        return wrapped
