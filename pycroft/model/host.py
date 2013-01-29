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
#from sqlalchemy.dialects import postgresql
from pycroft.model import dormitory
from pycroft.model.session import session
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.types import Integer
from sqlalchemy.types import String
import ipaddr
import re
from pycroft.model.host_alias import  ARecord, AAAARecord


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

    name = Column(String(255))

    user = relationship("User",
        backref=backref("server_hosts", cascade="all, delete-orphan"))


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
            raise Exception("Multicast flag (least significant bit of "
                            "the first byte) is set!")
        return ':'.join(bytes).lower()


def _other_subnets_for_mac(net_device):
    """Helper function for duplicate MAC address checking.

    This retrieves a list of all Subnet addresses connected to any
    other NetDevice (i.e. not the given net_device) with the same MAC
    address as net_device.

    """
    return session.query(
        dormitory.Subnet.address
    ).filter(
        NetDevice.mac == net_device.mac,
        NetDevice.id != net_device.id,
    ).join(
        Ip
    ).distinct().all()


def _check_mac_unique_in_subnets(mapper, connection, target):
    """Check for common (i.e. duplicate) MAC addresses between
    different NetDevices on the same Subnet.

    MAC addresses are not uniquely associated to a NetDevice, i.e.
    there might be more than one NetDevice with a given MAC address,
    and as long as all those NetDevices have no Subnets in common,
    this is fine.  However, a given MAC address must not appear on
    more than one Netdevice on any given Subnet.

    This is called when adding new or udpdating existing NetDevices.

    """
    own_subnets = [(ip.subnet.address,)
                   for ip in target.ips
                   if ip.subnet is not None]
    other_subnets = _other_subnets_for_mac(target)

    if len(set(own_subnets).intersection(other_subnets)) > 0:
        raise Exception("Duplicate MAC address (already present on one "
                        "of the connected subnets)")


event.listen(NetDevice, "before_insert", _check_mac_unique_in_subnets,
             propagate=True)
event.listen(NetDevice, "before_update", _check_mac_unique_in_subnets,
             propagate=True)


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


def _check_subnet_macs_unique(mapper, connection, target):
    """Check for common (i.e. duplicate) MAC addresses between
    different NetDevices on the same Subnet.

    There might be more than one NetDevice with a given MAC
    address. As long as those NetDevices are not connected to a common
    subnet, this is fine. Also, a given NetDevice may have more than
    one Ip belonging to a given Subnet.

    This is called when adding or updating Ips.

    """
    if target.subnet is not None:
        own_subnet = target.subnet.address
        other_subnets = session.query(
            NetDevice.id,
            Ip.address,
            dormitory.Subnet.address
        ).filter(
            Ip.id != target.id,
            NetDevice.mac == target.net_device.mac,
            NetDevice.id != target.net_device.id
        ).join(
            Ip.net_device,
            Ip.subnet
        ).all()

        if own_subnet in [net for (_, _, net) in other_subnets]:
            raise Exception("Duplicate MAC address (already present on one "
                            "of the connected subnets)")


event.listen(Ip, "before_insert", _check_correct_ip_subnet)
event.listen(Ip, "before_insert", _check_subnet_macs_unique)
event.listen(Ip, "before_update", _check_correct_ip_subnet)
event.listen(Ip, "before_update", _check_subnet_macs_unique)

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