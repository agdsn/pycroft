#!/usr/bin/bash
sphinx-autobuild doc doc/_build/html -jauto --watch pycroft --watch doc/_static --watch ldap_sync "$@"
