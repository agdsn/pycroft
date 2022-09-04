"""
This package provides a standalone LDAP syncer.  For more information
on how to execute it, run ``python -m ldap_sync --help``.

The process is separated into the following steps:

1. Fetch the users/groups/properties we want to sync from the database
   (:mod:`ldap_sync.sources.db`)
2. Fetch the current users/groups/properties from the ldap (:mod:`ldap_sync.sources.ldap`)
3. Create a diff (:mod:`ldap_sync.diff_records`)
4. Execute the actions (:mod:`ldap_sync.execution`)
"""
import logging

logger = logging.getLogger('ldap_sync')
