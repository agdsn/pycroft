#!/usr/bin/env python
from migrate.versioning.shell import main
main(url='sqlite:///test_db.sqlite', debug='False', repository='migration')
