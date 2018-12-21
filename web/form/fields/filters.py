def empty_to_none(x):
    return None if not x else x


def to_lowercase(x):
    if type(x) is str:
        return x.lower()
    else:
        return x


def to_uppercase(x):
    if type(x) is str:
        return x.upper()
    else:
        return x
