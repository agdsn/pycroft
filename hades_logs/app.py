from celery import Celery


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
    def __init__(self, *a, routing_key=None, **kw):
        super().__init__(*a, **kw)
        self.routing_key = routing_key
        self.conf['task_default_exchange'] = 'hades.agent.rpc'
        self.conf['task_default_exchange_type'] = 'topic'
        self.conf['task_create_missing_queues'] = True
        self.conf['task_serializer'] = 'json'
        self.conf['event_serializer'] = 'json'
        self.conf['result_serializer'] = 'json'
        self.conf['broker_transport_options'] = {
            "max_retries": 3,
            "interval_start": 0,
            "interval_step": 0.2,
            "interval_max": 0.5,
        }

    def signature(self, *a, **kw):
        if self.routing_key is not None:
            kw = kw.copy()
            kw.setdefault('options', {})
            kw['options']['routing_key'] = self.routing_key
        return super().signature(*a, **kw)
