import pytest

from pycroft.helpers.interval import IntervalSet, closed, openclosed


class TestTypeMangling:
    def test_type_mangling(self):
        # TODO one test per assertion and `target` / `base` as fixtures
        target = IntervalSet([closed(0, 1)])
        # Creation
        assert target == IntervalSet(closed(0, 1))
        assert target == IntervalSet([closed(0, 1)])
        with pytest.raises(TypeError):
            IntervalSet(0)
        # Union
        base = IntervalSet(())
        assert target == base | IntervalSet(closed(0, 1))
        assert target == base | closed(0, 1)
        assert target == base | [closed(0, 1)]
        # Intersection
        base = target | closed(1, 2)
        assert target == base & IntervalSet(openclosed(0, 1))
        assert target == base & openclosed(0, 1)
        assert target == base & [openclosed(0, 1)]
        # Difference
        assert target == base - IntervalSet(openclosed(1, 2))
        assert target == base - openclosed(1, 2)
        assert target == base - [openclosed(1, 2)]
