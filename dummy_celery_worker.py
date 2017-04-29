import os

from celery import Celery

app = Celery('dummy_tasks', broker=os.environ['TEST_HADES_BROKER_URI'],
             backend=os.environ['TEST_HADES_RESULT_BACKEND_URI'])

@app.task
def get_port_auth_attempts(nasipaddress, nasportid):
    return ["Success!", "No success! :-(",
            "Gotten: {}/{}".format(nasipaddress, nasportid)]
