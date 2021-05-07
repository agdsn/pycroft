def validate_attribute_type(key, value):
    """Validate if some attribute value has the correct type.

    This concerns the single-valuedness, which is estimated using
    a hard-coded, global list :py:obj:`SINGLE_VALUED_ATTRIBUTES`
    capturing teh most relevant attributes restricted to a single
    value.
    """
    if key in SINGLE_VALUED_ATTRIBUTES and isinstance(value, list):
        raise ValueError(f"Value '{value}' for key '{key}' should be a single value")
    if key not in SINGLE_VALUED_ATTRIBUTES and not isinstance(value, list):
        raise ValueError(f"Value '{value}' for key '{key}' should be a list")


def get_all_objects(connection, base):
    connection.search(search_base=base, search_filter='(objectclass=*)', attributes='*')
    return connection.response


SINGLE_VALUED_ATTRIBUTES = ['uidNumber', 'gidNumber', 'homeDirectory',
                            'gecos', 'shadowMin', 'shadowMax',
                            'shadowFlag', 'shadowExpire', 'loginShell']
