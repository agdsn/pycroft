# -*- coding: utf-8 -*-
"""
    pycroft.model.properties
    ~~~~~~~~~~~~~~

    :copyright: (c) 2011 by AG DSN.
"""
from datetime import datetime
from base import ModelBase
from sqlalchemy import ForeignKey, and_, or_
from sqlalchemy import Column
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.types import BigInteger, Integer, DateTime
from sqlalchemy.types import String


class Group(ModelBase):
    name = Column(String(255), nullable=False)
    discriminator = Column('type', String(17), nullable=False)
    __mapper_args__ = {'polymorphic_on': discriminator}

    users = relationship("User",
        secondary="membership",
        primaryjoin="Membership.group_id==Group.id",
        secondaryjoin="User.id==Membership.user_id",
        foreign_keys=lambda: [Membership.user_id, Membership.group_id],
        viewonly=True)

    active_users = relationship("User",
        secondary="membership",
        primaryjoin=lambda: and_(Membership.group_id==Group.id, Membership.active),
        secondaryjoin="User.id==Membership.user_id",
        foreign_keys=lambda: [Membership.user_id, Membership.group_id],
        viewonly=True)


class Membership(ModelBase):
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)

    # many to one from Membership to Group
    group_id = Column(Integer, ForeignKey('group.id', ondelete="CASCADE"),
        nullable=False)
    group = relationship("Group", backref=backref("memberships",
        cascade="all, delete-orphan",
        order_by='Membership.id'))

    # many to one from Membership to User
    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"),
        nullable=False)
    user = relationship("User", backref=backref("memberships",
        cascade="all, delete-orphan",
        order_by='Membership.id'))

    def __init__(self, *args, **kwargs):
        super(Membership, self).__init__(*args, **kwargs)
        if self.start_date is None:
            self.start_date = datetime.now()

    @hybrid_property
    def active(self):
        now = datetime.now()
        if now < self.start_date:
            return False
        if self.end_date is not None:
            if self.end_date < now:
                return False
        return True

    @active.expression
    def active(cls):
        import pycroft.model.session as session
        now = session.session.now_sql()
        return and_(cls.start_date <= now, or_(cls.end_date == None, cls.end_date >= now))

    @validates('end_date')
    def validate_end_date(self, _, value):
        if value is None:
            return value
        assert value >= self.start_date, "you set end date before start date!"
        return value

    @validates('start_date')
    def validate_start_date(self, _, value):
        assert value is not None, "start_date cannot be None!"
        if self.end_date is not None:
            assert value <= self.end_date, "you set start date behind end date!"
        return value

    def disable(self):
        now = datetime.now()
        if self.start_date > now:
            self.end_date = self.start_date
        else:
            self.end_date = now


class Property(ModelBase):
    name = Column(String(255), nullable=False)

    # many to one from Property to PropertyGroup
    # nullable=True
    property_group_id = Column(Integer, ForeignKey("propertygroup.id"),
        nullable=False)
    #TODO prüfen, ob cascade Properties löscht, wenn zugehörige PGroup deleted
    property_group = relationship("PropertyGroup",
        backref=backref("properties", cascade="all,delete"))


class PropertyGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'propertygroup'}
    id = Column(Integer, ForeignKey('group.id'), primary_key=True,
        nullable=False)

    def has_property(self, property_name):
        if Property.q.filter_by(property_group_id=self.id,
            name=property_name).count() > 0:
            return True

        return False


class TrafficGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'trafficgroup'}
    id = Column(Integer, ForeignKey('group.id'), primary_key=True,
        nullable=False)
    # in byte per seven days, zero is no limit
    traffic_limit = Column(BigInteger, nullable=False)


property_categories = [
    (u"Rechte Nutzer",
     [
         (u"internet", u"Nutzer darf sich mit dem Internet verbinden"),
         (u"mail", u"Nutzer darf E-Mails versenden (und empfangen)"),
         (u"ssh_helios", u"Nutzer darf sich mit SSH auf Helios einloggen"),
         (u"homepage_helios", u"Nutzer darf eine Hompage auf Helios anlegen"),
         (u"no_pay", u"Nutzer muss keinen Semesterbeitrag zahlen")
     ]
        ),
    (u"Verbote Nutzer",
     [
         (u"no_internet", u"Nutzer darf sich NICHT mit dem Internet verbinden"),
         (u"no_ssh_helios",
          u"Nutzer darf sich NICHT mit SSH auf Helios einloggen")
     ]
        ),
    (u"Nutzeradministration",
     [
         (u"user_show", u"Nutzer darf andere Nutzer in der Usersuite sehen"),
         (u"user_change", u"Nutzer darf Nutzer erstellen, ändern, löschen"),
         (u"mac_change", u"Nutzer darf MAC Adressen ändern")
     ]
        ),
    (u"Finanzadministration",
     [
         (u"finance_show", u"Nutzer darf Finanzen einsehen"),
         (u"finance_change", u"Nutzer darf Finanzen ändern")
     ]
        ),
    (u"Infrastrukturadministration",
     [
         (u"infrastructure_show", u"Nutzer darf Infrastruktur ansehen"),
         (u"infrastructure_change", u"Nutzer darf Infrastruktur verwalten")
     ]
        )
]


def get_properties():
    """ Join all categories to one list of property strings.
    :return: list of property identifiers
    """
    properties = []
    for category in property_categories:
        for property in category[1]:
            properties.append(property[0])

    return properties
