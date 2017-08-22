class HadesError(Exception):
    pass


class HadesTimeout(TimeoutError, HadesError):
    pass


class HadesConfigError(RuntimeError, HadesError):
    pass


class HadesOperationalError(RuntimeError, HadesError):
    pass
