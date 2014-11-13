# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.


def bake_endpoint(blueprint, fn):
    return "{}.{}".format(blueprint.name, fn.__name__)
