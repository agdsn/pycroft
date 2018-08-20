def or_default(value, default):
    """
    Helps to avoid using a temporary variable in cases similiar to the following::

        if slow_function() is not None:
            return slow_function()
        else:
            return default
    """
    return value if value is not None else default


def map_or_default(value, mapper, default):
    """
    Helps to avoid using a temporary variable in cases similiar to the following::

        if slow_function() is not None:
            return mapper(slow_function())
        else:
            return default
    """
    return mapper(value) if value is not None else default
