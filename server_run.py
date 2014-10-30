#!/usr/bin/env python2
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import argparse

def server_run(args):
    from web import make_app
    from pycroft import config

    app = make_app()
    app.debug = args.debug

    app.config['MAX_CONTENT_LENGTH'] = int(config["file_upload"]
                                            ["max_file_size"])
    app.config['UPLOAD_FOLDER'] = config["file_upload"]["temp_dir"]

    app.run(debug=args.debug, port=args.port,
            host="0.0.0.0" if args.exposed else None)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pycroft launcher")
    parser.add_argument("--debug", action="store_true",
                        help="run in debug mode")
    parser.add_argument("--exposed", action="store_true",
                        help="expose server on network")
    parser.add_argument("-p","--port", action="store",
                        help="port to run Pycroft on", type=int, default=5000)

    server_run(parser.parse_args())
