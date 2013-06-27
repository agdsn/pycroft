from pycroft.model import session
from pycroft.model.host_alias import HostAlias, ARecord, AAAARecord, MXRecord, \
    CNameRecord, NSRecord, SRVRecord


def delete_alias(alias_id, commit=True):
    """
    This method deletes an alias.

    :param alias_id: the id of the alias which should be deleted
    :param commit: flag which indicates whether the session should be
                   committed or not. Default: True
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
    if commit:
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

    return alias


def _create_alias(type, commit=True, *args, **kwargs):
    """
    This method will create a new dns record.

    :param type: the type of the alias (equals the discriminator of the alias)
    :param args: the positionals which will be passed to the constructor of
                 the alias
    :param kwargs: the arguments which will be passed to the constructor of
                   the alias
    :param commit: flag which indicates whether the session should be
                   committed or not. Default: True
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
    if commit:
        session.session.commit()

    return alias

# Wrapper functions around the _create_alias function for each record type

def create_arecord(host, name, address, time_to_live=None, commit=True):
    """
    This method will create a new a-record

    :param host: the host
    :param name: the name of the alias
    :param time_to_live: the ttl of the alias
    :param address: the ip address which should be associated with the
                       a-record
    :param commit: flag which indicates whether the session should be
                   committed or not. Default: True
    :return: the created a-record
    """

    return _create_alias("arecord", host=host, name=name,
                         time_to_live=time_to_live, address=address,
                         commit=commit)


def create_aaaarecord(host, name, address, time_to_live=None,
                      commit=True):
    """
    This method will create a new aaaa-record

    :param host: the host
    :param name: the name of the alias
    :param time_to_live: the ttl of the alias
    :param address: the ip address which should be associated with the
                       aaaa-record
    :param commit: flag which indicates whether the session should be
                   committed or not. Default: True
    :return: the created aaaa-record
    """

    return _create_alias("aaaarecord", name=name, host=host,
                         time_to_live=time_to_live, address=address,
                         commit=commit)


def create_mxrecord(host, server, domain, priority, commit=True):
    """
    This method will create a new mx-record

    :param host: the host
    :param server: the server
    :param domain: the domain
    :param priority: priority
    :param commit: flag which indicates whether the session should be
                   committed or not. Default: True
    :return: the created mx-record
    """

    return _create_alias("mxrecord", host=host, server=server,
                         domain=domain, priority=priority, commit=commit)


def create_cnamerecord(host, name, alias_for, commit=True):
    """
    This method will create a new cname-record

    :param host: the host
    :param name: the alias for the a- or aaaarecord
    :param alias_for: the record we want to specify an alias
    :param commit: flag which indicates whether the sesssion should
                   be committed or not. Default: True
    :return: the created cname-record
    """

    return _create_alias("cnamerecord", host=host, name=name,
                         alias_for=alias_for, commit=commit)


def create_nsrecord(host, domain, server, time_to_live=None, commit=True):
    """
    This method will create a new ns-record.

    :param host: the host
    :param domain: the domain
    :param server: the server
    :param time_to_live: the time the record should be valid
    :param commit: flag which indicates whether the session should be
                   committed or not. Default: True
    :return: the created ns-record
    """

    return _create_alias("nsrecord", host=host, domain=domain,
                         server=server, time_to_live=time_to_live,
                         commit=commit)


def create_srvrecord(host, service, priority, weight, port, target,
                     time_to_live=None, commit=True):
    """
    This method will create a new srv-record.

    :param host: the host
    :param service: the service
    :param priority: the priority
    :param weight: the weight
    :param port: the port
    :param target: the target
    :param time_to_live: the time the record should be valid
    :param commit: flag which indicates whether the session should be
                   committed or not. Default: True
    :return: the created srv-record
    """

    return _create_alias("srvrecord", host=host, service=service,
                         priority=priority, weight=weight, port=port,
                         target=target, time_to_live=time_to_live,
                         commit=commit)