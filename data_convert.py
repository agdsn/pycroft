# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from legacy import convert
from pycroft import model

if __name__ == "__main__":

    print "drop old db model"
    model.drop_db_model()

    print "create new db model"
    model.create_db_model()

    print "convert data"
    convert.do_convert()
    print "complete"
