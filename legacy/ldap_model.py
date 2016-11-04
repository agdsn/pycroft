from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session


Base = declarative_base()


class Nutzer(Base):
    __tablename__ = 'ldap_nutzer'

    uid = Column(String, primary_key=True)
    mail = Column(String)
    userPassword = Column(String, nullable=False)
    homeDirectory = Column(String, nullable=False)
    uidNumber = Column(Integer, nullable=False)
    gidNumber = Column(Integer, nullable=False)
    loginShell = Column(String, nullable=False)

    @classmethod
    def from_ldap_attributes(cls, result):
        return cls(
            uid=result['uid'][0],
            mail=result.get('mail'),
            # we can safely assume users only have exactly one password.
            # I checked this for our production data on 2016-11-03.
            userPassword=result['userPassword'][0],
            homeDirectory=result['homeDirectory'],
            uidNumber=result['uidNumber'],
            gidNumber=result['gidNumber'],
            loginShell=result['loginShell'],
        )
