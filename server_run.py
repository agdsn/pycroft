# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from web import make_app

if __name__ == "__main__":
    app = make_app()
    app.debug = True

    app.run(debug=True)
