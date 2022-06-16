#!/bin/bash
# we don't want errexit
set -uo pipefail

mypy pycroft/lib/traffic.py | tee mypy_results.log;
export mypy_status=$?
python ./scripts/render_mypy_results.py mypy_results.log
exit $mypy_status
