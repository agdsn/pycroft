from pycroft.model.base import IntegerIdModel, ModelBase
from pycroft.model.user import User
from pycroft.model.types import IPAddress, IPNetwork

from sqlalchemy import Column, ForeignKey, Integer, CHAR, String
from sqlalchemy.orm import backref


class PublicIP(IntegerIdModel):
    address = Column(IPAddress, nullable=False, unique=True)
    owner = Column(User, backref=backref("public-ip"))


class PrivateNet(IntegerIdModel):
    subnet = Column(IPNetwork,nullable=False,unique=True)
    router_ip = Column(IPAddress,nullable=False)


class Translation(ModelBase):
    public_ip = Column(PublicIP,ForeignKey(PublicIP.address),primary_key=True)
    private_ip = Column(PrivateNet, backref("translation"),
                        primary_key=True, unique=True)


class Forwarding(IntegerIdModel):
    public_ip = Column(PublicIP,ForeignKey(PublicIP.address),primary_key=True)
    source_port = Column(Integer)
    protocol = Column(CHAR(5))
    destination_port = Column(Integer)
    destination_ip = Column(IPAddress)
    comment = Column(String(150))