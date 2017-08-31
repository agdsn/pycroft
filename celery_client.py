#!/bin/env python3
"""
Usage:
~~~~~~

This is a wrapper for the celery cli, which us usually invoked by just
 typing `celery`.

$ python3 -m celery_client <celery_command>

For instance, the shell can be used this way:

```
$ python3 -m celery_client shell  # for a shell
Python 3.4.2 (default, Oct  8 2014, 10:45:20)
[GCC 4.9.1] on linux
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>> from hades_logs import hades_logs
>>> hades_logs.celery is app
True
>>> app
<HadesCelery hades.tasks:0x7f75170794a8>
```

"""
import sys

from web.app import make_app
from hades_logs import hades_logs

if __name__ == '__main__':
    app = make_app()
    with app.app_context():
        hades_logs.celery.start(sys.argv)
