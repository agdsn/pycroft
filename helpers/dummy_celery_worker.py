import os
from datetime import datetime
from time import sleep

from celery import Celery

app = Celery('dummy_tasks', broker=os.environ['TEST_HADES_BROKER_URI'],
             backend=os.environ['TEST_HADES_RESULT_BACKEND_URI'])


@app.task
def get_auth_attempts_at_port(nas_ip_address, nas_port_id, limit=100):
    if nas_port_id == 'magic_sleep':
        # sleep for 10 seconds, which is longer than the default
        sleep(10)
        return []

    if nas_ip_address != '141.30.223.206' or nas_port_id != 'C6':
        return []
    return [
        # (packettype, replymessage, username, auth_date, egress_vlan)
        # TODO: What VLAN should there be on Auth-Reject?  In any
        # case, it will be unused.
        ("Auth-Reject", "", "00:de:ad:be:ef:00", datetime(2017, 4, 20, 18, 25), None),
        ("Auth-Access", "Wu5_untagged", "00:de:ad:be:ef:00", datetime(2017, 4, 20, 18, 20), 15),
        ("Auth-Access", "unknown", "00:de:ad:be:ef:01", datetime(2017, 4, 20, 18, 5), 1001),
        ("Auth-Access", "traffic", "00:de:ad:be:ef:00", datetime(2017, 4, 20, 18, 0), 1001),
    ][:limit]
