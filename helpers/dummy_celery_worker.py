"""

Usage:

$ python3 helpers/dummy_celery_worker.py worker


"""
import os
from datetime import datetime
from time import sleep

from celery import Celery

app = Celery('dummy_tasks', broker=os.environ['TEST_HADES_BROKER_URI'],
             backend=os.environ['TEST_HADES_RESULT_BACKEND_URI'])


def _vlan_as_attrlist(vlan):
    return [('Egress-VLAN-Name', vlan)] if vlan is not None else []


@app.task
def get_auth_attempts_at_port(nas_ip_address, nas_port_id, limit=100):
    """Simulate the Hades task with the same name

    A set of static entries is returned except if both parameters
    evaluate to ``False``.  The latter results in an empty list.

    :param str nas_ip_address:
    :param str nas_port_id: If set to ``'magic_sleep'``, trigger the
        special behavior of sleeping for 10 seconds and returning
        ``[]``
    :param int limit: Limits the response to the given count of
        entries
    """
    if nas_port_id == 'magic_sleep':
        # sleep for 10 seconds, which is longer than the default
        sleep(10)
        return []

    if not nas_ip_address and not nas_port_id:
        return []

    return [
        ("00:de:ad:be:ef:00", "Access-Reject", [""], _vlan_as_attrlist(None),
         datetime(2017, 4, 20, 18, 25).timestamp()),
        ("00:de:ad:be:ef:00", "Access-Accept", ["Wu5_untagged"], _vlan_as_attrlist('"2Wu5"'),
         datetime(2017, 4, 20, 18, 20).timestamp()),
        ("00:de:ad:be:ef:01", "Access-Accept", ["unknown"], _vlan_as_attrlist('"2hades_unauth"'),
         datetime(2017, 4, 20, 18, 5).timestamp()),
        ("00:de:ad:be:ef:00", "Access-Accept", ["traffic"], _vlan_as_attrlist('"2hades_unauth"'),
         datetime(2017, 4, 20, 18, 0).timestamp()),
    ][:limit]

if __name__ == '__main__':
    import sys
    app.start(sys.argv)
