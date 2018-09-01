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
        self.conf['CELERY_DEFAULT_EXCHANGE'] = 'hades.agent.rpc'
        self.conf['CELERY_DEFAULT_EXCHANGE_TYPE'] = 'topic'
        self.conf['CELERY_CREATE_MISSING_QUEUES'] = True
        self.conf['CELERY_TASK_SERIALIZER'] = 'json'
        self.conf['CELERY_EVENT_SERIALIZER'] = 'json'
        self.conf['CELERY_RESULT_SERIALIZER'] = 'json'

    def signature(self, *a, **kw):
        if self.routing_key is not None:
            kw = kw.copy()
            kw.setdefault('options', {})
            kw['options']['routing_key'] = self.routing_key
        return super().signature(*a, **kw)
