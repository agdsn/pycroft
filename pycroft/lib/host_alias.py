# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.model.hosts import HostAlias, ARecord, AAAARecord, CNameRecord, \
    MXRecord, SRVRecord, NSRecord
from pycroft.model import session

def delete_alias(alias_id):
    """
    This method deletes an alias.

    :param alias_id: the id of the alias which should be deleted
    :return: the deleted alias
    """
    alias = HostAlias.q.get(alias_id)

    if (alias is None):
        raise ValueError("The given id is not correct!")

    if (alias.discriminator == "arecord"):
        record = ARecord.q.filter(ARecord.id == alias_id).one()
    elif (alias.discriminator == "aaaarecord"):
        record = AAAARecord.q.filter(AAAARecord.id == alias_id).one()
    elif (alias.discriminator == "cnamerecord"):
        record = CNameRecord.q.filter(CNameRecord.id == alias_id).one()
    elif (alias.discriminator == "mxrecord"):
        record = MXRecord.q.filter(MXRecord.id == alias_id).one()
    elif (alias.discriminator == "srvrecord"):
        record = SRVRecord.q.filter(SRVRecord.id == alias_id).one()
    elif (alias.discriminator == "nsrecord"):
        record = NSRecord.q.filter(NSRecord.id == alias_id).one()
    else:
        raise ValueError("Unknown record type: %s" % (alias.discriminator))

    session.session.delete(record)
    session.session.commit()

    return alias


def change_alias(alias, **kwargs):
    """
    This method will change the attributes given in the kwargs of the alias.

    :param alias: the alias which should be changed
    :param kwargs: the attributes which should be changed in the format
            attribute_name = new_value
    :return: the changed record
    """
    for arg in kwargs:
        try:
            getattr(alias, arg)
        except AttributeError:
            raise ValueError("The alias has no argument %s" % (arg,))
        else:
            setattr(alias, arg, kwargs[arg])

    session.session.commit()

    return  alias


def create_alias(type, *args, **kwargs):
    """
    This method will create a new dns record.

    :param type: the type of the alias (equals the discriminator of the alias)
    :param kwargs: the arguments which will be passed to the constructor of the alias
    :return: the created record
    """

    discriminator = str(type).lower()

    if (discriminator == "arecord"):
        alias = ARecord(*args, **kwargs)
    elif (discriminator == "aaaarecord"):
        alias = AAAARecord(*args, **kwargs)
    elif (discriminator == "cnamerecord"):
        alias = CNameRecord(*args, **kwargs)
    elif (discriminator == "mxrecord"):
        alias = MXRecord(*args, **kwargs)
    elif (discriminator == "nsrecord"):
        alias = NSRecord(*args, **kwargs)
    elif (discriminator == "srvrecord"):
        alias = SRVRecord(*args, **kwargs)
    else:
        raise ValueError("unknown record type: %s" % (type))

    session.session.add(alias)
    session.session.commit()

    return alias
