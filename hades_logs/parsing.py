from collections import defaultdict, namedtuple
from datetime import datetime, timezone
from functools import partial

_radius_log_entry = namedtuple(
    'RadiusLogEntry',
    ['mac', 'reply', 'groups', 'raw_attributes', 'timestamp']
)

class ParsingError(ValueError):
    pass


def parse_vlan(vlan):
    stripped = vlan.strip('"')
    prefix, name = stripped[:1], stripped[1:]
    if not name:
        raise ParsingError("VLAN identifier has no Name: {}".format(name))
    try:
        taggedness = {'1': "tagged", '2': "untagged"}[prefix]
    except KeyError:
        raise ParsingError("VLAN identifier must start with '1' or '2': {}"
                           .format(stripped))
    return "{} ({})".format(name, taggedness)


def attrlist_to_dict(attrlist):
    """Convert a list of (key, value) tuples to a dict of lists"""
    d = defaultdict(list)
    for key, val in attrlist:
        d[key].append(val)
    return d


class RadiusLogEntry(_radius_log_entry):
    """Class representing a parsed hades log entry.

    This is namedtuple subclass conforming with the tuples returned by
    ``get_auth_attempts_at_port`` from the Hades RPC API.

    It provides convenient access to whether the request was accepted
    (:py:meth:`__bool__`), the :py:attr:`vlans`, time, and equality.
    """
    @property
    def accepted(self):
        """Return whether the reply says ``"Access-Accept"``"""
        return self.reply == "Access-Accept"

    @property
    def attributes(self):
        """The attributes provided as a dict of lists."""
        return attrlist_to_dict(self.raw_attributes)

    @property
    def vlans(self):
        """Return the string representation of each VLAN"""
        # lookup defaults to [] as self.attributes is a defaultdict
        raw_vlans = self.attributes['Egress-VLAN-Name']
        return [parse_vlan(v) for v in raw_vlans]

    @property
    def time(self):
        return datetime.fromtimestamp(self.timestamp, tz=timezone.utc)

    def __bool__(self):
        """Evaluates to :py:prop:`self.accepted`"""
        return self.accepted

    def effectively_equal(self, other):
        relevant_attributes = set(_radius_log_entry._fields) - {'timestamp'}
        try:
            return all(getattr(self, a) == getattr(other, a)
                       for a in relevant_attributes)
        except AttributeError:
            return False


def _eq(a, b):
    return a == b


def reduce_to_first_occurrence(iterable, comparator=_eq):
    """Reduces equivalent blocks of an iterable to the first occurence

    :param iterable: Any iterable of homogeneous type with respect to
        the comparator
    :param comparator: An equivalence relation.  Must be transitive,
        because the comparison is always run against the first
        representative of each equivalent block, not the actual
        previous element.
    """
    iterator = iter(iterable)
    try:
        previous = next(iterator)
    except StopIteration:
        return

    yield previous

    for element in iterator:
        if not comparator(previous, element):
            yield element
            previous = element


reduce_radius_logs = partial(reduce_to_first_occurrence,
                             comparator=RadiusLogEntry.effectively_equal)
