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
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.types import Integer
from sqlalchemy.types import String
import ipaddr

import re

from pycroft.helpers import host_helper


class Host(ModelBase):
    hostname = Column(String(255), nullable=False)
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    # many to one from Host to User
    user = relationship("User", backref=backref("hosts", cascade="all, delete-orphan"))
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    # many to one from Host to Room
    room = relationship(dormitory.Room, backref=backref("hosts"))
    room_id = Column(Integer, ForeignKey("room.id"), nullable=True)


class HostAlias(ModelBase):
    content = Column(String(255), nullable=False)
    discriminator = Column('type', String(50))
    __mapper_args__ =  {'polymorphic_on': discriminator}

    def __init__(self, content):
        self.content = content

    # many to one from HostAlias to Host
    host = relationship("Host", backref=backref("aliases"))
    host_id = Column(Integer, ForeignKey("host.id"), nullable=False)


class ARecord(HostAlias):
    time_to_live = Column(Integer)  # optional time to live attribute
    ip = Column(String(51), nullable=False)
    __mapper_args__ = {'polymorphic_identity':'arecord'}

    def __init__(self, name, ip, time_to_live = None):
        super(ARecord, self).__init__(name)
        self.ip = ip
        self.time_to_live = time_to_live

    @validates('ip')
    def validate_ip (self, _, value):
        assert value.subnet.ip_type == "4"
        return value

    @property
    def gen_entry(self):
        if not self.time_to_live:
            return u"%s IN A %s" % (self.content, self.ip)
        else:
            return u"%s %s IN A %s" % (self.content, self.time_to_live, self.ip)


class AAAARecord(HostAlias):
    time_to_live = Column(Integer)  # optional time to live attribute
    ip = Column(String(51), nullable=False)
    __mapper_args__ = {'polymorphic_identity':'aaaarecord'}

    def __init__(self, name, ip, time_to_live = None):
        super(AAAARecord, self).__init__(name)
        self.ip = ip
        self.time_to_live = time_to_live

    @validates('ip')
    def validate_ip(self, _, value):
        assert value.subnet.ip_type == "6"
        return value

    @property
    def gen_entry(self):
        if not self.time_to_live:
            return u"%s IN AAAA %s" % (self.content, self.ip)
        else:
            return u"%s %s IN AAAA %s" % (self.content, self.time_to_live, self.ip)

class MXRecord(HostAlias):
    domain = Column(String(255), nullable=False)
    priority = Column(Integer, nullable=False)
    __mapper_args__ = {'polymorphic_identity':'mxrecord'}

    def __init__(self, server_name, domain, priority):
        super(MXRecord, self).__init__(server_name)
        self.domain = domain
        self.priority = priority

    @property
    def gen_entry(self):
        return u"%s IN MX %s %s" % (self.domain, self.priority, self.content)


class CNameRecord(HostAlias):
    alias_for = Column(Integer, nullable=False)
    __mapper_args__ = {'polymorphic_identity':'cnamerecord'}

    def __init__(self, name, alias_for):
        super(CNameRecord, self).__init__(name)
        self.alias_for = alias_for

    @property
    def gen_entry(self):
        return u"%s IN CNAME %s" % (self.content, self.alias_for)


class NSRecord(HostAlias):
    domain = Column(String(255), nullable=False)
    time_to_live = Column(Integer)
    __mapper_args__ = {'polymorphic_identity':'nsrecord'}

    def __init__(self, server, domain, time_to_live = None):
        super(NSRecord, self).__init__(server)
        self.domain = domain
        self.time_to_live = time_to_live

    @property
    def gen_entry(self):
        if not self.time_to_live:
            return u"%s IN NS %s" % (self.domain, self.content)
        else:
            return u"%s %s IN NS %s" % (self.domain, self.time_to_live, self.content)


class NetDevice(ModelBase):
    #mac = Column(postgresql.MACADDR, nullable=False)
    mac = Column(String(12), nullable=False)

    # one to one from PatchPort to NetDevice
    patch_port_id = Column(Integer, ForeignKey('patchport.id'), nullable=True)
    patch_port = relationship("PatchPort", backref=backref("net_device",
                                                          uselist=False))

    host_id = Column(Integer, ForeignKey("host.id", ondelete="CASCADE"), nullable=False)
    host = relationship("Host", backref=backref("net_devices", cascade="all, delete-orphan"))

    mac_regex = re.compile(r"^[a-f0-9]{2}(:[a-f0-9]{2}){5}$")


    @validates('mac')
    def validate_mac(self, _, value):
        if not NetDevice.mac_regex.match(value):
            raise Exception("invalid MAC address!")
        if int(value[1], base=16) & 1:
            raise Exception("Multicast-Flag (least significant bit im "
                            "ersten Byte gesetzt)!")
        return value


class Ip(ModelBase):
    def __init__(self, *args, **kwargs):
        super(Ip, self).__init__(*args, **kwargs)

        if self.address is not None and self.subnet is not None:
            assert self.is_ip_valid, "Subnet does not contain the ip"

    address = Column(String(51), unique=True, nullable=False)
    #address = Column(postgresql.INET, nullable=True)

    net_device_id = Column(Integer, ForeignKey('netdevice.id', ondelete="CASCADE"), nullable=False)
    net_device = relationship(NetDevice, backref=backref("ips", cascade="all, delete-orphan"))

    host = relationship(Host,
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
            assert self._ip_subnet_valid(self.address, value), \
                    "Given subnet does not contain the ip"
        return value

    @validates("address")
    def validate_address(self, _, value):
        if value is None:
            return value
        if self.subnet is not None:
            assert self._ip_subnet_valid(value, self.subnet), \
                    "Subnet does not contain the given ip"
        return value


def _check_correct_ip_subnet(mapper, connection, target):
    if target.address is not None and target.subnet is not None:
        assert target.is_ip_valid, "Subnet does not contain the ip"


event.listen(Ip, "before_insert", _check_correct_ip_subnet)
event.listen(Ip, "before_update", _check_correct_ip_subnet)


class Switch(Host):
    __mapper_args__ = {'polymorphic_identity': 'switch'}
    id = Column(Integer, ForeignKey('host.id'), primary_key=True)

    name = Column(String(127), nullable=False)

    management_ip_id = Column(Integer,
        ForeignKey("ip.id",
            use_alter=True,
            name="fk_management_ip"),
        unique=True,)
    management_ip = relationship("Ip", post_update=True)


def _check_correct_management_ip(mapper, connection, target):
    assert target.management_ip is not None, "A management ip has to be set"

    ips = []
    for dev in target.net_devices:
        ips.extend(dev.ips)

    assert target.management_ip in ips, \
            "the management ip is not valid on this switch"


event.listen(Switch, "before_insert", _check_correct_management_ip)
event.listen(Switch, "before_update", _check_correct_management_ip)
