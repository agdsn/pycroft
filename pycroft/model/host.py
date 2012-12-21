# -*- coding: utf-8 -*-
"""
    pycroft.model.hosts
    ~~~~~~~~~~~~~~

    This module contains the classes Host, NetDevice, Switch.

    :copyright: (c) 2011 by AG DSN.
"""
from base import ModelBase
from sqlalchemy import ForeignKey, event
from sqlalchemy import Column
from sqlalchemy.orm import Session
#from sqlalchemy.dialects import postgresql
from pycroft.model import dormitory, port
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.types import Integer
from sqlalchemy.types import String
import ipaddr
import re


class Host(ModelBase):
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    #TODO make user_id nullable after last import of mysql data
    # many to one from Host to User
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"),
        nullable=True)

    # many to one from Host to Room
    room = relationship(dormitory.Room, backref=backref("hosts"))
    room_id = Column(Integer, ForeignKey("room.id"), nullable=True)


class UserHost(Host):
    id = Column(Integer, ForeignKey('host.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'user_host'}

    # one to one from Host to User
    user = relationship("User",
        backref=backref("user_host", cascade="all, delete-orphan",
            uselist=False))


class ServerHost(Host):
    id = Column(Integer, ForeignKey('host.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'server_host'}

    user = relationship("User",
        backref=backref("server_hosts", cascade="all, delete-orphan"))


class HostAlias(ModelBase):
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    # many to one from HostAlias to Host
    host = relationship("Host",
        backref=backref("aliases", cascade="all, delete-orphan"))
    host_id = Column(Integer, ForeignKey("host.id", ondelete="CASCADE"),
        nullable=False)


class ARecord(HostAlias):
    id = Column(Integer, ForeignKey('hostalias.id'), primary_key=True)
    name = Column(String(255), nullable=False)
    time_to_live = Column(Integer)  # optional time to live attribute

    # many to one from ARecord to Ip
    address = relationship("Ip")
    address_id = Column(Integer, ForeignKey("ip.id"),
        nullable=False)

    __mapper_args__ = {'polymorphic_identity': 'arecord'}

    @validates('address')
    def validate_address(self, _, value):
        assert value.subnet.ip_type == "4"
        return value

    @property
    def information_human(self):
        "returns all information readable for a human"
        if self.time_to_live is not None:
            return u"%s points to %s with TTL %s" % (
                self.name, self.address.address, self.time_to_live)
        else:
            return u"%s points to %s" % (self.name, self.address.address)

    @property
    def gen_entry(self):
        if not self.time_to_live:
            return u"%s IN A %s" % (self.name, self.address.address)
        else:
            return u"%s %s IN A %s" % (
                self.name, self.time_to_live, self.address.address)

    @property
    def gen_reverse_entry(self):
        reversed_address = ".".join(reversed(self.address.address.split(".")))
        if not self.time_to_live:
            return u"%s.in-addr.arpa. IN PTR %s" % (reversed_address, self.name)
        else:
            return u"%s.in-addr.arpa. %s IN PTR %s" % (
                reversed_address, self.time_to_live,
                self.name)


class AAAARecord(HostAlias):
    id = Column(Integer, ForeignKey('hostalias.id'), primary_key=True)
    name = Column(String(255), nullable=False)
    time_to_live = Column(Integer)  # optional time to live attribute

    # many to one from ARecord to Ip
    address = relationship("Ip")
    address_id = Column(Integer, ForeignKey("ip.id"),
        nullable=False)

    __mapper_args__ = {'polymorphic_identity': 'aaaarecord'}

    @validates('address')
    def validate_address(self, _, value):
        assert value.subnet.ip_type == "6"
        return value

    @property
    def information_human(self):
        "returns all information readable for a human"
        if self.time_to_live is not None:
            return u"%s points to %s with TTL %s" % (
                self.name, self.address.address, self.time_to_live)
        else:
            return u"%s points to %s" % (self.name, self.address.address)

    @property
    def gen_entry(self):
        if not self.time_to_live:
            return u"%s IN AAAA %s" % (self.name, self.address.address)
        else:
            return u"%s %s IN AAAA %s" % (
                self.name, self.time_to_live, self.address.address)

    @property
    def gen_reverse_entry(self):
        reversed_address = ".".join(["%x" % ord(b) for b in reversed(
            (ipaddr.IPv6Address(self.address.address)).packed)])
        if not self.time_to_live:
            return u"%s.ip6.arpa. IN PTR %s" % (reversed_address, self.name)
        else:
            return u"%s.ip6.arpa. %s IN PTR %s" % (
                reversed_address, self.time_to_live, self.name)


class MXRecord(HostAlias):
    id = Column(Integer, ForeignKey('hostalias.id'), primary_key=True)
    server = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=False)
    priority = Column(Integer, nullable=False)
    __mapper_args__ = {'polymorphic_identity': 'mxrecord'}

    @property
    def information_human(self):
        "returns all information readable for a human"
        return u"%s is mail-server for %s with priority %s" % (
            self.server, self.domain, self.priority)

    @property
    def gen_entry(self):
        return u"%s IN MX %s %s" % (self.domain, self.priority, self.server)


class CNameRecord(HostAlias):
    id = Column(Integer, ForeignKey('hostalias.id'), primary_key=True)
    name = Column(String(255), nullable=False)

    alias_for_id = Column(Integer,
        ForeignKey("hostalias.id", ondelete="CASCADE"), nullable=False)
    alias_for = relationship("HostAlias",
        primaryjoin=alias_for_id == HostAlias.id,
        backref = backref('cnames', cascade='all, delete-orphan')
    )

    __mapper_args__ = {
        'polymorphic_identity': 'cnamerecord',
        'inherit_condition': (id == HostAlias.id)
    }

    @validates('alias_for')
    def validate_alias_for(self, _, value):
        # check if the alias is of the correct type! just arecord and
        # aaaarecord are allowed
        assert value.discriminator == "arecord" or\
               value.discriminator == "aaaarecord"
        assert value.name != self.name

        return value

    @property
    def information_human(self):
        "returns all information readable for a human"
        return u"%s is alias for %s" % (self.name, self.alias_for.name)

    @property
    def gen_entry(self):
        return u"%s IN CNAME %s" % (self.name, self.alias_for.name)


class NSRecord(HostAlias):
    id = Column(Integer, ForeignKey('hostalias.id'), primary_key=True)
    domain = Column(String(255), nullable=False)
    server = Column(String(255), nullable=False)
    time_to_live = Column(Integer)
    __mapper_args__ = {'polymorphic_identity': 'nsrecord'}

    @property
    def information_human(self):
        "returns all information readable for a human"
        return u"TODO"

    @property
    def gen_entry(self):
        if not self.time_to_live:
            return u"%s IN NS %s" % (self.domain, self.server)
        else:
            return u"%s %s IN NS %s" % (
                self.domain, self.time_to_live, self.server)


class SRVRecord(HostAlias):
    id = Column(Integer, ForeignKey('hostalias.id'), primary_key=True)
    service = Column(String(255), nullable=False)
    time_to_live = Column(Integer)
    priority = Column(Integer, nullable=False)
    weight = Column(Integer, nullable=False)
    port = Column(Integer, nullable=False)
    target = Column(String(255), nullable=False)
    __mapper_args__ = {'polymorphic_identity': 'srvrecord'}

    @property
    def information_human(self):
        "returns all information readable for a human"
        return u"TODO"

    @property
    def gen_entry(self):
        if not self.time_to_live:
            return u"%s IN SRV %s %s %s %s" % (
                self.service, self.priority, self.weight,
                self.port, self.target)
        else:
            return u"%s %s IN SRV %s %s %s %s" % (
                self.service, self.time_to_live, self.priority,
                self.weight, self.port, self.target)


class Switch(Host):
    __mapper_args__ = {'polymorphic_identity': 'switch'}
    id = Column(Integer, ForeignKey('host.id'), primary_key=True)

    name = Column(String(127), nullable=False)

    management_ip = Column(String(127), nullable=False)

    user = relationship("User",
        backref=backref("switches", cascade="all, delete-orphan"))


def create_mac_regex():
    """Helper function to create a regular expression object for matching
    MAC addresses in different formats. A valid MAC address is a sequence of
    6 bytes coded as hexadecimal digits separated by a symbol after either one,
    two or three bytes. It is also possible that there is no separating symbol.

    The following examples all encode the same MAC address:
    001122334455
    00-11-22-33-44-55
    00:11:22:33:44:55
    0011.2233.4455
    001122-334455

    After a successful match, the individual bytes bytes, as well as the
    separator symbols can be accessed using symbolic group names.
    byte1, byte2, byte3, byte4, byte5, byte6: The n-th byte
    sep1, sep2, sep3: The one, two or three byte separator char or None
    :return: a regular expression object
    """
    # Byte represented by 2 hexadecimal digits
    BYTE_PATTERN = r'(?:[a-fA-F0-9]{2})'
    # Pattern for the most significant byte
    # Does not allow the first bit to be set (multicast flag)
    MOST_SIGNIFICANT_BYTE_PATTERN = r'(?:[a-fA-F0-9][02468ACE])'
    # Allowed 1 byte separators
    SEP1_PATTERN = r'[-:]'
    # Allowed 2 byte separators
    SEP2_PATTERN = r'\.'
    # Allowed 3 byte separators
    SEP3_PATTERN = r'-'
    expr = []
    # Begin of string
    expr.append(r'^')
    # Most significant byte (Sixth byte)
    # The leftmost byte has highest order due to Big Endian
    expr.append(r'(?P<byte6>%s)' % BYTE_PATTERN)
    # Try to match sep1 after the 6th byte
    expr.append(r'(?P<sep1>%s)?' % SEP1_PATTERN)
    # Fifth byte
    expr.append(r'(?P<byte5>%s)' % BYTE_PATTERN)
    # If sep1 hasn't matched, try to match the sep2 pattern after the second
    # byte else the same sep1 match must match here too.
    expr.append(r'(?(sep1)(?P=sep1)|(?P<sep2>%s)?)' % SEP2_PATTERN)
    # Fourth byte
    expr.append(r'(?P<byte4>%s)' % BYTE_PATTERN)
    # If neither sep1 nor sep2 have matched, try sep3 pattern after third byte.
    # If sep1 has matched before, the same sep1 match must match here too.
    expr.append(r'(?(sep1)(?P=sep1)|(?(sep2)|(?P<sep3>%s)?))' % SEP3_PATTERN)
    # Third byte
    expr.append(r'(?P<byte3>%s)' % BYTE_PATTERN)
    # If sep1 has matched before, the same sep1 match must match after the
    # fourth byte.
    # The same applies to sep2.
    expr.append(r'(?(sep1)(?P=sep1))(?(sep2)(?P=sep2))')
    # Second byte
    expr.append(r'(?P<byte2>%s)' % BYTE_PATTERN)
    # If sep1 has matched before, the same sep1 match must match after the
    # fifth byte.
    expr.append(r'(?(sep1)(?P=sep1))')
    # Least significant byte (First byte)
    expr.append(r'(?P<byte1>%s)' % BYTE_PATTERN)
    # End of string
    expr.append(r'$')
    return re.compile(''.join(expr))


class NetDevice(ModelBase):
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    #mac = Column(postgresql.MACADDR, nullable=False)
    mac = Column(String(17), nullable=False)

    mac_regex = create_mac_regex()

    host_id = Column(Integer, ForeignKey('host.id', ondelete="CASCADE"),
        nullable=False)

    @validates('mac')
    def validate_mac(self, _, value):
        match = NetDevice.mac_regex.match(value)
        if not match:
            raise Exception("Invalid MAC address!")
        groupdict = match.groupdict()
        bytes =  [groupdict['byte6'], groupdict['byte5'], groupdict['byte4'],
                  groupdict['byte3'], groupdict['byte2'], groupdict['byte1']]
        if int(bytes[0], base=16) & 1:
            raise Exception("Multicast-Flag (least significant bit im "
                            "ersten Byte gesetzt)!")
        return ':'.join(bytes).lower()


class UserNetDevice(NetDevice):
    id = Column(Integer, ForeignKey('netdevice.id'), primary_key=True)

    __mapper_args__ = {'polymorphic_identity': "user_net_device"}

    host = relationship("UserHost",
        backref=backref("user_net_device", uselist=False,
            cascade="all, delete-orphan"))


class ServerNetDevice(NetDevice):
    id = Column(Integer, ForeignKey('netdevice.id'), primary_key=True)

    __mapper_args__ = {'polymorphic_identity': "server_net_device"}

    host = relationship("ServerHost",
        backref=backref("server_net_devices", cascade="all, delete-orphan"))

    switch_port_id = Column(Integer, ForeignKey('switchport.id'),
        nullable=False)
    switch_port = relationship("SwitchPort")


class SwitchNetDevice(NetDevice):
    id = Column(Integer, ForeignKey('netdevice.id'), primary_key=True)

    __mapper_args__ = {'polymorphic_identity': "switch_net_device"}

    host = relationship("Switch",
        backref=backref("switch_net_devices", cascade="all, delete-orphan"))


class Ip(ModelBase):
    def __init__(self, *args, **kwargs):
        super(Ip, self).__init__(*args, **kwargs)

        if self.address is not None and self.subnet is not None:
            assert self.is_ip_valid, "Subnet does not contain the ip"

    address = Column(String(51), unique=True, nullable=False)
    #address = Column(postgresql.INET, nullable=True)

    net_device_id = Column(Integer,
        ForeignKey('netdevice.id', ondelete="CASCADE"), nullable=False)
    net_device = relationship(NetDevice,
        backref=backref("ips", cascade="all, delete-orphan"))

    host = relationship("Host",
        secondary="netdevice",
        backref=backref("ips"),
        viewonly=True)

    subnet_id = Column(Integer, ForeignKey("subnet.id"), nullable=False)
    subnet = relationship("Subnet", backref=backref("ips"))

    def change_ip(self, ip, subnet):
        self.subnet = None
        self.address = ip
        self.subnet = subnet

    def _ip_subnet_valid(self, ip, subnet):
        return ipaddr.IPAddress(ip) in ipaddr.IPNetwork(subnet.address)

    @property
    def is_ip_valid(self):
        if self.address is None or self.subnet is None:
            return False
        return self._ip_subnet_valid(self.address, self.subnet)

    @validates('subnet')
    def validate_subnet(self, _, value):
        if value is None:
            return value
        if self.address is not None:
            assert self._ip_subnet_valid(self.address, value),\
            "Given subnet does not contain the ip"
        return value

    @validates("address")
    def validate_address(self, _, value):
        if value is None:
            return value
        if self.subnet is not None:
            assert self._ip_subnet_valid(value, self.subnet),\
            "Subnet does not contain the given ip"
        return value


def _check_correct_ip_subnet(mapper, connection, target):
    if target.address is not None and target.subnet is not None:
        assert target.is_ip_valid, "Subnet does not contain the ip"


event.listen(Ip, "before_insert", _check_correct_ip_subnet)
event.listen(Ip, "before_update", _check_correct_ip_subnet)

def _delete_corresponding_record(mapper, connection, target):
    ip_id = target.id

    # First check for ARecords
    record = ARecord.q.filter(ARecord.address_id == ip_id).first()
    if record is not None:
        raise ValueError("There is still an ARecord which points to this address")

    # Afterwards check for AAAARecords
    record =  AAAARecord.q.filter(AAAARecord.address_id == ip_id).first()
    if record is not None:
        raise ValueError("There is still an AAAARecord which points to this address")


event.listen(Ip, 'before_delete', _delete_corresponding_record)