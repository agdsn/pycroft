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
    if nas_port_id == 'magic_sleep':
        # sleep for 10 seconds, which is longer than the default
        sleep(10)
        return []

    if nas_ip_address != '141.30.223.206' or nas_port_id != 'C6':
        return []
    return [
        ("00:de:ad:be:ef:00", "Access-Reject", [""], _vlan_as_attrlist(None),
         datetime(2017, 4, 20, 18, 25)),
        ("00:de:ad:be:ef:00", "Access-Accept", ["Wu5_untagged"], _vlan_as_attrlist('"2Wu5"'),
         datetime(2017, 4, 20, 18, 20)),
        ("00:de:ad:be:ef:01", "Access-Accept", ["unknown"], _vlan_as_attrlist('"2hades_unauth"'),
         datetime(2017, 4, 20, 18, 5)),
        ("00:de:ad:be:ef:00", "Access-Accept", ["traffic"], _vlan_as_attrlist('"2hades_unauth"'),
         datetime(2017, 4, 20, 18, 0)),
    ][:limit]
