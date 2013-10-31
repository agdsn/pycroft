# Copyright (c) 2013 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from web import make_app
from pycroft.lib import config

if __name__ == "__main__":
    app = make_app()
    app.debug = True

    app.config['MAX_CONTENT_LENGTH'] = \
        int(config.get("file_upload")["max_file_size"])
    app.config['UPLOAD_FOLDER'] = config.get("file_upload")["temp_dir"]

    app.run(debug=True)
