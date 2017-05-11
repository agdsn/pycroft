from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session


Base = declarative_base()
metadata = Base.metadata


class Nutzer(Base):
    __tablename__ = 'ldap_nutzer'

    uid = Column(String, primary_key=True)
    mail = Column(String)
    userPassword = Column(String)
    homeDirectory = Column(String, nullable=False)
    uidNumber = Column(Integer, nullable=False)
    gidNumber = Column(Integer, nullable=False)
    loginShell = Column(String, nullable=False)
    aktiv = Column(Boolean, nullable=False)
    exaktiv = Column(Boolean, nullable=False)

    @classmethod
    def from_ldap_attributes(cls, result, group_mappings=None):
        if result.get('mail'):
            mail = result['mail'][0]
        else:
            mail = None

        uid = result['uid'][0]

        if group_mappings is not None:
            groups = [cn for cn, members in group_mappings.items()
                      if uid in members]
            if len(groups) > 1:
                raise ValueError("Non-Disjoint group memberships: {}"
                                 .format(groups))
        else:
            groups = []

        if len(result['userPassword']) > 1:
            print("WARNING: User {} has more than one password!")

        _pw = result['userPassword'][0]
        if _pw is not None:
            # userPassword is given as byte (“Octet
            # String”). Reference:
            # https://tools.ietf.org/html/rfc2256#section-5.36
            pw = _pw.decode('utf-8')
        else:
            pw = None

        return cls(
            uid=uid,
            mail=mail,
            # we can safely assume users only have exactly one password.
            # I checked this for our production data on 2016-11-03.
            userPassword=pw,
            homeDirectory=result['homeDirectory'],
            uidNumber=result['uidNumber'],
            gidNumber=result['gidNumber'],
            loginShell=result['loginShell'],
            aktiv='Aktiv' in groups,
            exaktiv='Exaktiv' in groups,
        )
