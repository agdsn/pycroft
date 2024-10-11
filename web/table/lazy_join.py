import typing as t
from functools import wraps
from types import FunctionType
from typing import overload
from collections.abc import Generator, Callable


def filled_iter[_T](iter: t.Iterable[_T], filler: _T) -> t.Iterator[_T]:
    """Inbetween every iteration, yield a constant filler."""
    first = True
    for elem in iter:
        if not first:
            yield filler
        else:
            first = False
        yield elem


class HasDunderStr(t.Protocol):
    @t.override
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
    ) -> None:
        self.glue = glue
        self._components = components
        self.exhausted = False

    @property
    def _stringified_components(self) -> t.Iterator[str]:
        return ((str(c) if c is not None else "") for c in self._components)

    @t.override
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


_P = t.ParamSpec("_P")
DecoratedInType = Callable[
    _P,
    Generator[HasDunderStr | None, None, None]
    | t.Iterator[HasDunderStr | None]
    | t.Iterator[HasDunderStr],
]
DecoratedOutType = Callable[_P, LazilyJoined]


@overload
def lazy_join(func_or_glue: DecoratedInType) -> DecoratedOutType:
    ...


@overload
def lazy_join(func_or_glue: str) -> Callable[[DecoratedInType], DecoratedOutType]:
    ...


def lazy_join(
    func_or_glue: str | DecoratedInType,
) -> DecoratedOutType | Callable[[DecoratedInType], DecoratedOutType]:
    if isinstance(func_or_glue, FunctionType):
        # Return the wrapped function
        return LazyJoinDecorator()(func=t.cast(DecoratedInType, func_or_glue))
    # Return the decorator
    return LazyJoinDecorator(glue=t.cast(str, func_or_glue))


class LazyJoinDecorator:
    def __init__(self, glue: str = "") -> None:
        self.glue = glue

    def __call__(self, func: DecoratedInType) -> DecoratedOutType:
        @wraps(func)
        def wrapped(*a: _P.args, **kw: _P.kwargs) -> LazilyJoined:
            return LazilyJoined(func(*a, **kw), glue=self.glue)

        return wrapped
