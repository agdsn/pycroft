from pycroft.model import session
from pycroft.model.dns import Record, ARecord, AAAARecord, MXRecord, \
    CNameRecord, NSRecord, SRVRecord
from pycroft.lib.all import with_transaction


@with_transaction
def delete_record(record_id):
    """
    This method deletes an record.

    :param record_id: the id of the record which should be deleted
    :return: the deleted record
    """
    record = Record.q.get(record_id)

    if (record is None):
        raise ValueError("The given id is not correct!")

    if (record.discriminator == "arecord"):
        record = ARecord.q.filter(ARecord.id == record_id).one()
    elif (record.discriminator == "aaaarecord"):
        record = AAAARecord.q.filter(AAAARecord.id == record_id).one()
    elif (record.discriminator == "cnamerecord"):
        record = CNameRecord.q.filter(CNameRecord.id == record_id).one()
    elif (record.discriminator == "mxrecord"):
        record = MXRecord.q.filter(MXRecord.id == record_id).one()
    elif (record.discriminator == "srvrecord"):
        record = SRVRecord.q.filter(SRVRecord.id == record_id).one()
    elif (record.discriminator == "nsrecord"):
        record = NSRecord.q.filter(NSRecord.id == record_id).one()
    else:
        raise ValueError("Unknown record type: %s" % (record.discriminator))

    session.session.delete(record)
    return record


@with_transaction
def change_record(record, **kwargs):
    """
    This method will change the attributes given in the kwargs of the record.

    :param record: the record which should be changed
    :param kwargs: the attributes which should be changed in the format
            attribute_name = new_value
    :return: the changed record
    """
    for arg in kwargs:
        try:
            getattr(record, arg)
        except AttributeError:
            raise ValueError("The record has no argument %s" % (arg,))
        else:
            setattr(record, arg, kwargs[arg])

    return record


def _create_record(type, *args, **kwargs):
    """
    This method will create a new dns record.

    :param type: the type of the record (equals the discriminator of the record)
    :param args: the positionals which will be passed to the constructor of
                 the record
    :param kwargs: the arguments which will be passed to the constructor of
                   the record
    :return: the created record
    """

    discriminator = str(type).lower()

    if (discriminator == "arecord"):
        record = ARecord(*args, **kwargs)
    elif (discriminator == "aaaarecord"):
        record = AAAARecord(*args, **kwargs)
    elif (discriminator == "cnamerecord"):
        record = CNameRecord(*args, **kwargs)
    elif (discriminator == "mxrecord"):
        record = MXRecord(*args, **kwargs)
    elif (discriminator == "nsrecord"):
        record = NSRecord(*args, **kwargs)
    elif (discriminator == "srvrecord"):
        record = SRVRecord(*args, **kwargs)
    else:
        raise ValueError("unknown record type: %s" % (type))

    session.session.add(record)
    return record

# Wrapper functions around the _create_record function for each record type

@with_transaction
def create_arecord(host, name, address, time_to_live=None):
    """
    This method will create a new a-record

    :param host: the host
    :param name: the name of the record
    :param time_to_live: the ttl of the record
    :param address: the ip address which should be associated with the
                       a-record
    :return: the created a-record
    """

    return _create_record("arecord", host=host, name=name,
                         time_to_live=time_to_live, address=address)


@with_transaction
def create_aaaarecord(host, name, address, time_to_live=None):
    """
    This method will create a new aaaa-record

    :param host: the host
    :param name: the name of the record
    :param time_to_live: the ttl of the record
    :param address: the ip address which should be associated with the
                       aaaa-record
    :return: the created aaaa-record
    """

    return _create_record("aaaarecord", name=name, host=host,
                         time_to_live=time_to_live, address=address)


@with_transaction
def create_mxrecord(host, server, domain, priority):
    """
    This method will create a new mx-record

    :param host: the host
    :param server: the server
    :param domain: the domain
    :param priority: priority
    :return: the created mx-record
    """

    return _create_record("mxrecord", host=host, server=server,
                         domain=domain, priority=priority)


@with_transaction
def create_cnamerecord(host, name, record_for):
    """
    This method will create a new cname-record

    :param host: the host
    :param name: the record for the a- or aaaarecord
    :param record_for: the record we want to specify an record
    :return: the created cname-record
    """

    return _create_record("cnamerecord", host=host, name=name,
                         record_for=record_for)


@with_transaction
def create_nsrecord(host, domain, server, time_to_live=None):
    """
    This method will create a new ns-record.

    :param host: the host
    :param domain: the domain
    :param server: the server
    :param time_to_live: the time the record should be valid
    :return: the created ns-record
    """

    return _create_record("nsrecord", host=host, domain=domain,
                         server=server, time_to_live=time_to_live)


@with_transaction
def create_srvrecord(host, service, priority, weight, port, target,
                     time_to_live=None):
    """
    This method will create a new srv-record.

    :param host: the host
    :param service: the service
    :param priority: the priority
    :param weight: the weight
    :param port: the port
    :param target: the target
    :param time_to_live: the time the record should be valid
    :return: the created srv-record
    """

    return _create_record("srvrecord", host=host, service=service,
                         priority=priority, weight=weight, port=port,
                         target=target, time_to_live=time_to_live)