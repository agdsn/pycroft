import typing as t
from functools import wraps
from types import FunctionType
from typing import Generator, Callable, overload


def filled_iter(iter, filler):
    """Inbetween every iteration, yield a constant filler."""
    first = True
    for elem in iter:
        if not first:
            yield filler
        else:
            first = False
        yield elem


class HasDunderStr(t.Protocol):
    def __str__(self) -> str:
        ...


class LazilyJoined:
    """A string that consists of multiple components

    NOTE: Just like a generator, it will be exhausted after the first call!
    """

    glue: str
    _components: t.Iterable[HasDunderStr | None]
    exhausted: bool

    def __init__(
        self,
        components: t.Iterable[HasDunderStr | None],
        glue: str = "",
    ):
        self.glue = glue
        self._components = components
        self.exhausted = False

    @property
    def _stringified_components(self) -> t.Iterator[str]:
        return ((str(c) if c is not None else "") for c in self._components)

    def __str__(self) -> str:
        self._mark_exhausted()
        return self.glue.join(self._stringified_components)

    def __iter__(self) -> t.Iterator[str]:
        self._mark_exhausted()
        if self.glue:
            return filled_iter(self._stringified_components, filler=self.glue)
        return iter(self._stringified_components)

    def _mark_exhausted(self) -> None:
        if self.exhausted:
            raise RuntimeError("LazyJoined object already exhausted!"
                               " You may call __str__ or __iter__ only once."
                               " For re-use, turn it into a list.")
        self.exhausted = True


DecoratedInType = Callable[
    ..., Generator[HasDunderStr | None, None, None] | t.Iterator[HasDunderStr | None]
]
DecoratedOutType = Callable[..., LazilyJoined]

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
            return LazilyJoined(func(*a, **kw), glue=self.glue)

        return wrapped
