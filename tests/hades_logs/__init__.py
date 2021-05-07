import os


def get_hades_logs_config():
    return {
        'HADES_CELERY_APP_NAME': 'dummy_tasks',
        'HADES_BROKER_URI': os.environ['HADES_BROKER_URI'],
        'HADES_RESULT_BACKEND_URI': os.environ['HADES_RESULT_BACKEND_URI'],
        'HADES_ROUTING_KEY': None,
    }
