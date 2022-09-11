from celery import Celery


def http_worker_name() -> str | None:
    try:
        import uwsgi
    except ImportError:
        return "dev"
    return f"uwsgi worker {uwsgi.worker_id()}"


class HadesCelery(Celery):
    """Celery subclass complying with the Hades RPC API

    This subclass sets a few options in :meth:`__init__` such as the
    default exchange and hooks into :meth:`signature` to set a routing
    key if given.

    :param str routing_key: The routing key to enforce in the options
        given to :meth:`signature`.  For unicast messages it is
        usually of the format ``<site>`` or ``<site>.<node>``.  If not
        set, behavior of :meth:`signature` is unchanged.
    """

    def __init__(self, *a, task_default_exchange, result_exchange, routing_key, **kw):
        super().__init__(*a, **kw)
        self.routing_key = routing_key
        self.conf["task_default_routing_key"] = routing_key
        self.conf["task_default_exchange"] = task_default_exchange
        self.conf["result_exchange"] = result_exchange
        self.conf["result_exchange_type"] = "direct"
        self.conf["task_default_exchange_type"] = "topic"
        self.conf["task_create_missing_queues"] = False
        self.conf['task_serializer'] = 'json'
        self.conf['event_serializer'] = 'json'
        self.conf['result_serializer'] = 'json'
        self.conf['broker_transport_options'] = {
            "max_retries": 3,
            "interval_start": 0,
            "interval_step": 0.2,
            "interval_max": 0.5,
            "client_properties": {
                "connection_name": f"pycroft hades_logs client @{http_worker_name()}"
            },
        }

    def signature(self, *a, **kw):
        if self.routing_key is not None:
            kw = kw.copy()
            kw.setdefault('options', {})
            kw['options']['routing_key'] = self.routing_key
        return super().signature(*a, **kw)
