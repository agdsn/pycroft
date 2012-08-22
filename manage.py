#!/usr/bin/env python
from migrate.versioning.shell import main
main(url='sqlite:////tmp/test.db', debug='False', repository='migration')
