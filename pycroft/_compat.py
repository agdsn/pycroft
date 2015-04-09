# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import sys
import operator


PY2 = sys.version_info[0] == 2

if PY2:
    chr = unichr
    text_type = unicode
    string_types = (unicode, str)
    integer_types = (int, long)
    int_to_byte = chr

    xrange = xrange
    from future_builtins import filter as ifilter, map as imap, zip as izip
    from itertools import ifilterfalse, izip_longest
    iterkeys = operator.methodcaller("iterkeys")
    itervalues = operator.methodcaller("itervalues")
    iteritems = operator.methodcaller("iteritems")
    reduce = reduce

    from StringIO import StringIO
    from cStringIO import StringIO as BytesIO
    NativeStringIO = BytesIO

else:
    chr = chr
    text_type = str
    string_types = (str, )
    integer_types = (int, )

    xrange = range
    ifilter = filter
    from itertools import filterfalse, zip_longest
    ifilterfalse = filterfalse
    izip_longest = zip_longest
    imap = map
    izip = zip
    from functools import reduce

    iterkeys = operator.methodcaller("keys")
    itervalues = operator.methodcaller("values")
    iteritems = operator.methodcaller("items")

    from io import StringIO, BytesIO
    NativeStringIO = StringIO


def with_metaclass(meta, base=object):
    return meta("NewBase", (base,), {})
