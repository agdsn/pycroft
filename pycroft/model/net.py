# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import ipaddr
from sqlalchemy import Column, Enum, Integer, ForeignKey, String, Table, event
from sqlalchemy.orm import relationship, backref, object_session
from pycroft.lib.net import MacExistsException
from pycroft.model.base import ModelBase
from pycroft.model.host import NetDevice, IP
from pycroft.model.types import IPAddress, IPNetwork


class VLAN(ModelBase):
    name = Column(String(127), nullable=False)
    tag = Column(Integer, nullable=False)

    dormitories = relationship(
        "Dormitory", backref=backref("vlans"),
        secondary=lambda: association_table_dormitory_vlan)


association_table_dormitory_vlan = Table(
    'association_dormitory_vlan',
    ModelBase.metadata,
    Column('dormitory_id', Integer, ForeignKey('dormitory.id')),
    Column('vlan_id', Integer, ForeignKey(VLAN.id)))


class Subnet(ModelBase):
    address = Column(IPNetwork, nullable=False)
    gateway = Column(IPAddress)
    primary_dns_zone_id = Column(Integer, ForeignKey("dns_zone.id"),
                                 nullable=False)
    primary_dns_zone = relationship("DNSZone", foreign_keys=[primary_dns_zone_id])
    reverse_dns_zone_id = Column(Integer, ForeignKey("dns_zone.id"),
                                 nullable=False)
    reverse_dns_zone = relationship("DNSZone", foreign_keys=[reverse_dns_zone_id])
    reserved_addresses = Column(Integer, default=0, nullable=False)

    # many to many from Subnet to VLAN
    vlans = relationship(VLAN, backref=backref("subnets"),
                         secondary=lambda: association_table_subnet_vlan)

    @property
    def netmask(self):
        net = ipaddr.IPNetwork(self.address)
        return str(net.netmask)

    @property
    def ip_version(self):
        return ipaddr.IPNetwork(self.address).version


association_table_subnet_vlan = Table(
    "association_subnet_vlan",
    ModelBase.metadata,
    Column("subnet_id", Integer, ForeignKey(Subnet.id)),
    Column("vlan_id", Integer, ForeignKey(VLAN.id)))


def _other_subnets_for_mac(net_device):
    """Helper function for duplicate MAC address checking.

    This retrieves a list of all Subnet addresses connected to any
    other NetDevice (i.e. not the given net_device) with the same MAC
    address as net_device.

    :param net_device: The NetDevice we are interested in.
    :return: List of all Subnet addresses connected to a different NetDevice
    with the same MAC address as net_device.

    """
    return object_session(net_device).query(
        Subnet.address
    ).filter(
        NetDevice.mac == net_device.mac,
        NetDevice.id != net_device.id,
    ).join(
        IP,
        NetDevice
    ).distinct().all()


def _check_mac_unique_in_subnets(mapper, connection, target):
    """Check for common (i.e. duplicate) MAC addresses between
    different NetDevices on the same Subnet.

    MAC addresses are not uniquely associated to a NetDevice, i.e.
    there might be more than one NetDevice with a given MAC address,
    and as long as all those NetDevices have no subnets in common,
    this is fine.  However, a given MAC address must not appear on
    more than one NetDevice on any given Subnet.

    This is called when adding new or updating existing NetDevices.

    """
    own_subnets = [(ip.subnet.address,)
                   for ip in target.ips
                   if ip.subnet is not None]
    other_subnets = _other_subnets_for_mac(target)

    if len(set(own_subnets).intersection(other_subnets)) > 0:
        raise MacExistsException("Mac already exists in this subnet!")


event.listen(NetDevice, "before_insert", _check_mac_unique_in_subnets,
             propagate=True)
event.listen(NetDevice, "before_update", _check_mac_unique_in_subnets,
             propagate=True)


def _check_subnet_macs_unique(mapper, connection, target):
    """Check for common (i.e. duplicate) MAC addresses between
    different NetDevices on the same Subnet.

    There might be more than one NetDevice with a given MAC
    address. As long as those NetDevices are not connected to a common
    subnet, this is fine. Also, a given NetDevice may have more than
    one IP belonging to a given Subnet.

    This is called when adding or updating Ips.

    """
    if target.subnet is not None:
        own_subnet = target.subnet.address
        other_subnets = object_session(target).query(
            NetDevice.id,
            IP.address,
            Subnet.address
        ).filter(
            IP.id != target.id,
            NetDevice.mac == target.net_device.mac,
            NetDevice.id != target.net_device.id
        ).join(
            IP.net_device,
            IP.subnet
        ).all()

        if own_subnet in [net for (_, _, net) in other_subnets]:
            raise MacExistsException("Duplicate MAC address (already present "
                                     "on one of the connected subnets)")

event.listen(IP, "before_insert", _check_subnet_macs_unique)
event.listen(IP, "before_update", _check_subnet_macs_unique)
