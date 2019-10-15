import unittest
from contextlib import contextmanager
from typing import TypeVar, List, ContextManager, Tuple, overload, Dict, Sequence


class AssertionMixin(unittest.TestCase):
    T = TypeVar('T')
    @contextmanager
    def assert_list_items(self, collection: List[T], expected_length=1) \
            -> ContextManager[Tuple[T, ...]]:
        self.assertEqual(len(collection), expected_length)
        yield tuple(collection)

    TKey = TypeVar('TKey')
    TValue = TypeVar('TValue')
    @overload
    def assert_dict_items(self, collection: Dict[TKey, TValue], expected_keys: TKey) \
        -> ContextManager[TValue]: ...

    @contextmanager
    def assert_dict_items(self, collection: Dict[TKey, TValue], expected_keys: Sequence[TKey]) \
            -> ContextManager[Tuple[TValue, ...]]:
        if isinstance(expected_keys, Sequence) and not isinstance(expected_keys, str):
            self.assertEqual(collection.keys(), set(expected_keys))
            yield tuple(collection[key] for key in expected_keys)
        else:
            key = expected_keys
            self.assertEqual(collection.keys(), {key})
            yield collection[key]
