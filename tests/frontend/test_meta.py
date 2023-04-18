#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import pytest

from .fixture_helpers import serialize_formdata


@pytest.mark.meta
def test_serialize_formdata():
    assert serialize_formdata({"a": [1, 2], "b": [{"foo": "bar"}]}) == {
        "a-1": 1,
        "a-2": 2,
        "b-1-foo": "bar",
    }
