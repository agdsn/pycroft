# coding=utf-8
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from collections import defaultdict
from datetime import datetime, timedelta, date
import difflib
import logging as std_logging
log = std_logging.getLogger('import.translate')
import os
import sys
from itertools import islice

import ipaddr
from sqlalchemy.sql import null

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pycroft.model import (traffic, facilities, dns, user, net, port,
                           finance, session, host, config, logging, types)
from pycroft.lib.host import generate_hostname
from pycroft.helpers import user as usertools, AttrDict
from pycroft.helpers.interval import (open, closedopen, closed, IntervalSet,
                                      PositiveInfinity, NegativeInfinity)

from import_conf import *
from tools import TranslationRegistry
from reconstruct_memberships import membership_from_fees
# TODO: missing or incomplete translations for status/groups/permissions, patchport, traffic, incidents/log, vlans, dns, ...

ROOT_NAME = "agdsn"
ROOT_PASSWD = "test"

reg = TranslationRegistry()
anonymize_flag = False
a_uids = {None: None} # uid -> uid
a_rooms = {} # uid -> room

def a_uid(uid):
    return a_uids[uid] if anonymize_flag else uid


def a_room(uid, room_tuple):
    return a_rooms[uid] if anonymize_flag else room_tuple


def a(val, anon_val=None):
    return anon_val if anonymize_flag else val


@reg.provides(facilities.Site)
def generate_sites(data, resources):
    site_d = resources['site'] = {id_: facilities.Site(name=name)
                          for id_, name in site_name_map.items()}
    return site_d.values()


@reg.provides(facilities.Building)
def translate_buildings(data, resources):
    site_d = resources['site']

    b_d = resources['wheim'] = {}  # netusers.Wheim.id -> obj
    for _b in data['wheim']:
        b = facilities.Building(
            id=_b.wheim_id,
            site=site_d[building_site_map[_b.wheim_id]],
            short_name=_b.kuerzel,
            street=_b.str.replace(u'strasse', u'straße'),
            number=_b.hausnr)
        b_d[_b.wheim_id] = b
    return b_d.values()


@reg.provides(facilities.Room)
def translate_rooms(data, resources):
    b_d = resources['wheim']

    r_d = resources['zimmer'] = {}  # (wheim_id, etage, zimmernr) -> obj
    for _r in data['zimmer']:
        r = facilities.Room(
            building=b_d[_r.wheim_id],
            level=_r.etage,
            number=_r.zimmernr,
            inhabitable=True)

        # _r.etage is VARCHAR here,
        # conversion to int is needed since it's an int everywhere else
        r_d[(_r.wheim_id, int(_r.etage), _r.zimmernr)] = r
    return r_d.values()


@reg.provides(user.Property, user.PropertyGroup, user.Group)
def generate_groups(data, resources):
    properties_l = []
    g_d = resources['group'] = {}  # role -> PropertyGroup obj

    for role, (group_name, properties) in group_props.iteritems():
        g = user.PropertyGroup(name=group_name)
        g_d[role] = g
        for prop_name, modifier in properties.iteritems():
            properties_l.append(user.Property(
                name=prop_name, property_group=g, granted=modifier))
    return g_d.values()+properties_l


@reg.provides(logging.UserLogEntry)
def translate_logs(data, resources):
    # todo import userman.log
    # todo think of best way to import zih_incidents

    return []


@reg.provides(user.User, satisfies=(user.User.account_id,))
def translate_users(data, resources):
    r_d = resources['zimmer']

    objs = []
    u_d = resources['user'] = {}  # nutzer_id -> obj
    ul_d = resources['username'] = {}  # unix_account -> obj
    ou_d = resources['nutzer'] = {}  # nutzer_id -> legacy_obj

    ignored_rooms = []
    for _u in data['nutzer']:
        ou_d[_u.nutzer_id] = _u
        login = a(_u.unix_account.strip(), str(a_uid(_u.nutzer_id))) if _u.nutzer_id != 0 else ROOT_NAME
        if not user.User.login_regex.match(login):
            login = "user_{}".format(a_uid(_u.nutzer_id))
        if login != _u.unix_account and not anonymize_flag:
            log.warning("Renaming login '%s' to '%s'", _u.unix_account, login)

        _r = (_u.wheim_id, _u.etage, _u.zimmernr)
        try:
            room = r_d[a_room(_u.nutzer_id, _r)]
        except KeyError:
            ignored_rooms.append(a_room(_u.nutzer_id, _r))
            log.warning("Ignoring room %s not present in hp4108_ports", _r)
            room = None

        account_name = "Nutzerkonto von {}".format(a_uid(_u.nutzer_id))


        try:
            ldap_account = resources['ldap_accounts'][_u.unix_account]
        except KeyError:
            # use kwargs in order to not give the password hash
            ldap_kwargs = {'unix_account': None, 'email': None}
        else:
            ldap_kwargs = {
                'unix_account': resources['unix_accounts'][_u.unix_account],
                'email': ldap_account.mail,
            }
            if ldap_account.userPassword:
                ldap_kwargs['passwd_hash'] = ldap_account.userPassword

        u = user.User(
            id=a_uid(_u.nutzer_id),
            login=login,
            name=a(_u.vname+" "+_u.name, str(a_uid(_u.nutzer_id))),
            room=room,
            registered_at=_u.anmeldedatum,
            account=finance.Account(name=account_name, type="USER_ASSET"),
            **ldap_kwargs
        )

        objs.append(u)
        u_d[_u.nutzer_id] = u
        ul_d[_u.unix_account] = u

        objs.append(logging.UserLogEntry(
            author=u_d.get(0, None),
            message="User imported from legacy database netusers. "
                    "Legacy status: "+_u.status.short_str,
            user=u))

        # user comment
        if _u.comment:
            objs.append(logging.UserLogEntry(
                author=u_d.get(0, None),
                message="Legacy comment: "+_u.comment,
                user=u))

    if ignored_rooms:
        log.warning("Ignored {num} ({uniq}) rooms missing from hp4108port".format(
            num=len(ignored_rooms), uniq=len(set(ignored_rooms))))
    return objs


@reg.provides(user.UnixAccount, satisfies=(user.User.unix_account_id,))
def translate_unix_accounts(data, resources):
    objs = []
    # legacy ldap accounts needed later for: mail, pw hash
    ldap_accounts = resources['ldap_accounts'] = {}  # login → legacy ldap obj
    # new unix accounts needed for: id (foreign_key)
    unix_accounts = resources['unix_accounts'] = {}  # login → new obj

    for ldap_user in data['ldap_nutzer']:
        ldap_accounts[ldap_user.uid] = ldap_user
        acc = user.UnixAccount(
            uid=ldap_user.uidNumber,
            gid=ldap_user.gidNumber,
            home_directory=ldap_user.homeDirectory,
            login_shell=ldap_user.loginShell,
        )
        unix_accounts[ldap_user.uid] = acc
        objs.append(acc)

    return objs


@reg.provides(finance.Semester)
def translate_semesters(data, resources):
    sem_d = resources['semester'] = {}

    gauge_stype, gauge_year, gauge_num = ("ws", 2014, 25) #id=25000 for WS14/15
    day={"ws": 1, "ss": 1}
    month={"ws": 10, "ss": 4}

    def semester_begin_date(i):
        stype = "ss" if (i%2==0) ^ (gauge_stype == "ws") else "ws"
        years_to_gauge = i//2 + (i%2 if stype != "ws" else 0)
        return date(day=day[stype],
                    month=month[stype],
                    year=gauge_year+years_to_gauge)

    for _sem in data['semester']:
        num_semesters_to_gauge = _sem.id/1000-gauge_num
        # fee changes:
        #   ws02/03 1000: anm2500 sem1750 red450
        #   ss04 4000: anm2500 sem1500 red450
        #   ws14/15 25000: anm0 sem2000 red100
        s = finance.Semester(
            name=_sem.name,
            registration_fee=25.00 if _sem.id < 25000 else 0.,
            regular_semester_fee=17.50 if _sem.id < 40.00 else (15.00 if _sem.id < 25000 else 20.00),
            reduced_semester_fee=4.50 if _sem.id < 25000 else 1.00,
            late_fee=2.50,
            grace_period=timedelta(days=62),
            reduced_semester_fee_threshold=timedelta(days=62),
            payment_deadline=timedelta(days=31),
            allowed_overdraft=5.00,
            begins_on=semester_begin_date(num_semesters_to_gauge),
            ends_on=semester_begin_date(num_semesters_to_gauge+1)-timedelta(days=1))
        sem_d[_sem.id] = s

    # FIXME temporary workaround for missing SS16 in legacy data
    sem_d['ss16tmp'] = finance.Semester(name="SS16",
                          registration_fee=0,
                          regular_semester_fee=20,
                          reduced_semester_fee=1,
                          late_fee=2.50,
                          grace_period=timedelta(days=62),
                          reduced_semester_fee_threshold=timedelta(days=62),
                          payment_deadline=timedelta(days=31),
                          allowed_overdraft=5.00,
                          begins_on=date(2016, 4, 1),
                          ends_on=date(2016, 10, 1)-timedelta(days=1))
    return sem_d.values()


@reg.provides(finance.Account)
def translate_finance_accounts(data, resources):
    # TODO: look over this
    facc_types = {
        u"Startguthaben": "REVENUE",
        u"Bankkonto": "BANK_ASSET",
        u"Bankgebühren": "EXPENSE",
        u"Abgaben": "EXPENSE",  # Abgaben = ?
        u"Sonstige Ausgaben": "EXPENSE",
        u"Nutzerkonto": "ASSET",
        u"Forderungen": "ASSET",
        u"Verbindlichkeiten": "LIABILITY",  # offene Rechnungen
        u"Beiträge": "REVENUE",
        u"Spenden": "REVENUE",
        u"Aktive Technik": "EXPENSE",
        u"Passive Technik": "EXPENSE",
        u"Büromaterial": "EXPENSE",
        u"Öffentlichkeitsarbeit": "EXPENSE",
        u"Beitragsabschreibung": "EXPENSE",
        u"Fehlbuchung andere Sektionen": "EXPENSE",  # mein lieber Herr Finanzverein...
        u"Rücküberweisung": "EXPENSE",
        u"Import Zeu und Bor": "EXPENSE",
        u"Aufwandsentschädigungen": "EXPENSE",
    }

    objs = []
    a_d = resources['account'] = {}
    an_d = resources['accountname'] = {}
    for name, type in facc_types.items():
        a = finance.Account(name=name, type=type)
        objs.append(a)
        an_d[name] = a

    # TODO: Think about this, this is a pretty unstable/volatile way to do things,
    #  maybe just save the generated dict to a file to allow for manual changes and
    #  oversight
    for _a in data['finanz_konten']:
        acc_name = (difflib.get_close_matches(_a.name,
                                          facc_types.keys(),
                                          n=1,
                                          cutoff=0.5) or [None])[0]
        log.debug(u"   {} {} -> {}".format(_a.id, _a.name, acc_name))

        if acc_name:
            a_d[_a.id] = an_d[acc_name]

        # make sure all accounts that are mapped to None do not have any
        # transactions associated with them

        if (acc_name is None and (_a.haben_fb or _a.soll_fb or _a.bankbuchungen)):
            raise ValueError("No name found for account with transactions"
                             " (id={})".format(_a.id))

    return objs


@reg.provides(finance.BankAccount)
def generate_bank_account(data, resources):
    an_d = resources['accountname']

    bank_account = finance.BankAccount(
        name="Bankkonto 3120219540",
        bank="Ostsächsische Sparkasse Dresden",
        account_number="3120219540",
        routing_number="85050300",
        iban="DE61850503003120219540",
        bic="OSDDDE81XXX",
        account=an_d["Bankkonto"])

    resources['bank_account'] = bank_account
    return [bank_account]


def simple_transaction(amount, credit_account, debit_account, description,
                       valid_on, author, **tx_kwargs):
    transaction = finance.Transaction(
        description=description or "NO DESCRIPTION GIVEN",
        author=author,
        valid_on=valid_on,
        **tx_kwargs)
    credit_split = finance.Split(
        amount=amount,
        account=credit_account,
        transaction=transaction)
    debit_split = finance.Split(
        amount=-amount,
        account=debit_account,
        transaction=transaction)

    return transaction, credit_split, debit_split


# chooses the new account id given an old account id and user id
def get_acc(old_account_id, old_user_id, u_d, a_d):
    if old_user_id: # user referenced
        if old_user_id not in u_d: # but doesn't exist
            account_name = ("Nutzerkonto von gelöschtem Nutzer {}"
                            .format(old_user_id))
            u = user.User(
                id=a_uid(old_user_id),
                login="deleted_user_"+str(a_uid(old_user_id)),
                name="Gelöschter Nutzer "+str(a_uid(old_user_id)),
                registered_at=datetime.fromtimestamp(0),
                account=finance.Account(name=account_name, type="ASSET"))

            u_d[old_user_id] = u

        account = u_d[old_user_id].account
    else:
        account = a_d[old_account_id]

    return account


@reg.provides(finance.BankAccountActivity,
              satisfies=(finance.BankAccountActivity.transaction_id,
                         finance.BankAccountActivity.split))
def translate_bank_transactions(data, resources):
    bank_account = resources['bank_account']

    bt_d = resources['bank_transaction'] = {}
    for _bt in data['bank_transaction']:
        bt = finance.BankAccountActivity(
            id=_bt.bkid,
            bank_account=bank_account,
            amount=_bt.wert,
            reference=a(_bt.bes, "[redacted]"),
            original_reference=a(_bt.bes, "[redacted]"),
            other_account_number="NO NUMBER GIVEN", #TODO fill these properly, somehow
            other_routing_number="NO NUMBER GIVEN", #TODO
            other_name="NO NAME GIVEN", #TODO
            imported_at=_bt.valid_on,
            posted_on=_bt.valid_on,
            valid_on=_bt.valid_on,
            split=None)
        bt_d[_bt.bkid] = bt
    return bt_d.values()


@reg.requires_function(translate_bank_transactions)
@reg.provides(finance.Transaction, finance.Split)
def translate_finance_transactions(data, resources):
    a_d = resources['account']
    an_d = resources['accountname']
    u_d = resources['user']
    ul_d = resources['username']
    bt_d = resources['bank_transaction']

    objs = []

    #  § 199 Abs. 1 BGB
    # TODO write-offs? write off mail memberships, but not full fees
    # TODO reconstruct past memberships based on fees incurred
    # TODO inspect 4000 transaction on 10538

    for _bu in data['finance_transaction']:
        if _bu.wert == 0 and _bu.haben == _bu.soll:
            log.warning('Ignoring invalid zero-value transaction')
            continue

        tss = simple_transaction(
            id=_bu.fbid,
            author=ul_d.get(_bu.bearbeiter, u_d[0]),
            description=_bu.bes, valid_on=_bu.datum,
            posted_at=_bu.datum,
            credit_account=get_acc(_bu.haben, _bu.haben_uid, u_d, a_d),
            debit_account=get_acc(_bu.soll, _bu.soll_uid, u_d, a_d),
            amount=_bu.wert)

        objs.extend(tss)

    min_id = max(b.fbid for b in data['finance_transaction']) + 1
    for i, _bt in enumerate(data['accounted_bank_transaction']):
        transaction = finance.Transaction(
            id=min_id+i,
            description=a(_bt.bes, "[redacted]") or "NO DESCRIPTION GIVEN",
            author=ul_d.get(_bt.bearbeiter, u_d[0]),
            valid_on=_bt.valid_on,
            posted_at=_bt.posted_at)
        credit_split = finance.Split(
            amount=_bt.wert,
            account=an_d[u"Bankkonto"],
            bank_account_activity=bt_d[_bt.bkid],
            transaction=transaction,
        )
        debit_split = finance.Split(
            amount=-_bt.wert,
            account=get_acc(_bt.konto_id, _bt.uid, u_d, a_d),
            transaction=transaction,
        )
        objs.extend((transaction, credit_split, debit_split))

    return objs


@reg.provides(dns.DNSZone, dns.SOARecord,
              satisfies=(dns.SOARecord.name_id, dns.SOARecord.mname_id))
def generate_dns_zone(data, resources):
    primary_host_zone = dns.DNSZone(name="agdsn.tu-dresden.de")
    urz_zone = dns.DNSZone(name="urz.tu-dresden.de")
    soa_record = dns.SOARecord(
        name=dns.DNSName(name="@", zone=primary_host_zone),
        mname=dns.DNSName(name="rnadm", zone=urz_zone),
        rname="wuensch.urz.tu-dresden.de.",
        serial=2010010800,
        refresh=10800,
        retry=3600,
        expire=3600000,
        minimum=86400)
    resources['primary_host_zone'] = primary_host_zone
    resources['soa_record'] = soa_record
    return primary_host_zone, soa_record


@reg.provides(net.VLAN, net.Subnet)
def generate_subnets_vlans(data, resources):
    primary_host_zone = resources['primary_host_zone']

    s_d = resources['subnet'] = {}
    for _s in data['subnet']:
        address = ipaddr.IPv4Network(_s.net_ip + "/" + _s.netmask)
        try:
            vlan = net.VLAN(name=_s.vlan_name,
                            vid=vlan_name_vid_map[_s.vlan_name])
        except KeyError as e:
            log.warning("Ignoring subnet %s missing from vlan_name_vid_map",
                        _s.vlan_name)
            continue

        rev_dnszone_name = '.'.join(islice(
            reversed(address.ip.exploded.split('.')),
            min((address.max_prefixlen-address.prefixlen + 7//8), 1),
            4)) + ".in-addr.arpa" # cp. from pycroft/lib/net.py:ptr_name
        s = net.Subnet(address=address,
                       gateway=ipaddr.IPv4Address(_s.default_gateway),
                       primary_dns_zone=primary_host_zone,
                       reverse_dns_zone=dns.DNSZone(name=rev_dnszone_name),
                       description=_s.vlan_name,
                       vlan=vlan)
        s_d[_s.subnet_id] = s

    # TODO: note, missing transit, server and eduroam subnets

    return s_d.values()


@reg.provides(host.Host, host.Interface,
                host.ServerHost, host.UserHost, host.Switch,
                host.ServerInterface, host.UserInterface, host.SwitchInterface,
                host.IP, dns.AddressRecord,
              satisfies=(host.IP.interface_id, dns.AddressRecord.name_id))
def translate_hosts(data, resources):
    legacy_hostname_map = {}
    u_d = resources['user']
    s_d = resources['subnet']
    r_d = resources['zimmer']
    b_d = resources['wheim']
    primary_host_zone = resources['primary_host_zone']

    objs = []
    sw_d = resources['switch'] = {}  # switch dict: mgmt_ip -> obj

    def get_or_create_room(wheim_id, etage, zimmernr):
        try:
            room = r_d[(wheim_id, etage, zimmernr)]
        except KeyError:
            room = facilities.Room(building=b_d[wheim_id],
                                   level=etage,
                                   number=zimmernr or '?',
                                   inhabitable=False)

            r_d[(wheim_id, etage, zimmernr)] = room

        return room

    for _c in data['switch']:
        room = get_or_create_room(_c.c_wheim_id, _c.c_etage, _c.c_zimmernr)
        mgmt_ip_blocks = _c.c_ip.split(".")
        mgmt_ip_blocks[0] = mgmt_ip_blocks[1] = "10"
        mgmt_ip = ipaddr.IPv4Address(".".join(mgmt_ip_blocks))
        h = host.Switch(owner=u_d[0], name=_c.c_hname, management_ip=mgmt_ip, room=room)
        interface = host.SwitchInterface(host=h, mac=_c.c_etheraddr or "00:00:00:00:00:01", name="switch management interface")
        ip = host.IP(interface=interface, address=ipaddr.IPv4Address(_c.c_ip), subnet=s_d[_c.c_subnet_id])
        sw_d[mgmt_ip] = h
        objs.append(ip)

    for _c in data['server']:
        room = get_or_create_room(_c.c_wheim_id, _c.c_etage, _c.c_zimmernr)
        h = host.ServerHost(owner=u_d[0], name=_c.c_alias, room=room)
        interface = host.ServerInterface(host=h, mac=_c.c_etheraddr)
        ip = host.IP(interface=interface, address=ipaddr.IPv4Address(_c.c_ip), subnet=s_d[_c.c_subnet_id])
        hostname = legacy_hostname_map.get(_c.c_hname, _c.c_hname)
        if hostname and hostname != 'NULL':
            objs.append(dns.AddressRecord(name=dns.DNSName(name=hostname, zone=primary_host_zone), address=ip))
        else:
            objs.append(ip)

    for _c in data['userhost']:
        owner = u_d[_c.nutzer_id]
        h = host.UserHost(owner=owner, room=owner.room)
        interface = host.UserInterface(host=h, mac=_c.c_etheraddr)

        if _c.nutzer.status_id in (1, 2, 4, 5, 7, 12):
            hostname = generate_hostname(ipaddr.IPAddress(_c.c_ip))
            ip = host.IP(interface=interface, address=ipaddr.IPv4Address(_c.c_ip), subnet=s_d[_c.c_subnet_id])
            objs.append(dns.AddressRecord(name=dns.DNSName(name=hostname, zone=primary_host_zone), address=ip))
        else:
            objs.append(interface)
    return objs


@reg.provides(port.SwitchPatchPort)
def translate_ports(data, resources):
    sw_d = resources['switch']
    s_d = resources['subnet']
    r_d = resources['zimmer']

    objs = []
    for _sp in data['port']:
        mgmt_ip = _sp.ip and ipaddr.IPv4Address(_sp.ip)
        try:
            switch = sw_d[mgmt_ip]
        except KeyError as e:
            log.warning("Ignoring hp4108port {}/{} due to missing switch in "
                           "legacy db".format(mgmt_ip, _sp.port))
            continue

        port_name = _sp.port
        room = r_d[(_sp.wheim_id, int(_sp.etage), _sp.zimmernr)]
        subnet_id = building_subnet_map[room.building.id]
        sp = host.SwitchInterface(
            host=switch, name=port_name,
            mac="00:00:00:00:00:01",
            default_subnet=s_d[subnet_id])
        # TODO insert proper patch_port names
        pp = port.SwitchPatchPort(
            switch_interface=sp, name="?? ({})".format(port_name), room=room)
        objs.append(pp)

    return objs


@reg.provides(config.Config)
def generate_config(data, resources):
    g_d = resources['group']
    an_d = resources['accountname']
    primary_host_zone = resources['primary_host_zone']

    return [config.Config(
        member_group=g_d["member"],
        violation_group=g_d["suspended"],
        network_access_group=g_d["member"],  # todo: actual network_access_group
        away_group=g_d["away"],
        moved_from_division_group=g_d["moved_from_division"],
        already_paid_semester_fee_group=g_d["already_paid"],
        registration_fee_account=an_d[u"Beiträge"],
        semester_fee_account=an_d[u"Beiträge"],
        late_fee_account=an_d[u"Beiträge"],
        additional_fee_account=an_d[u"Beiträge"],
        user_zone=primary_host_zone
)]


@reg.requires_function(translate_finance_transactions, translate_semesters)
@reg.provides(user.Membership)
def reconstruct_memberships(data, resources):
    u_d = resources['user']
    g_d = resources['group']
    semesters = resources['semester'].values()

    n = AttrDict(ok=0, fixed=0, failed=0, unclassified=0, ignored=0)

    objs = []
    for i__u, _u in enumerate(data['nutzer']):
        u = u_d[_u.nutzer_id]
        if _u.nutzer_id == 0:
            u.passwd_hash = usertools.hash_password(ROOT_PASSWD)
            objs.append(user.Membership(user=u, group=g_d["root"], begins_at=null()))
        else:
            gname_duration = defaultdict(IntervalSet)
            gname_duration["member"], gname_duration["away"] = membership_from_fees(u, semesters, n)


            # if the membership could be reconstructed ending at the
            # beginning of the current month (last fee), delete the
            # ending and make it unbounded
            latest_membership_end = max(gname_duration['member']).end \
                                    if gname_duration['member'] else None

            if latest_membership_end is not None and \
                   latest_membership_end.replace(day=1) == date.today().replace(day=1):
                gname_duration['member'] += IntervalSet(closedopen(latest_membership_end, None))

            for gname in status_groups_map[_u.status_id]: # current memberships
                gname_duration[gname] += IntervalSet(
                    closedopen(datetime.now().date(), None))

            for gname, duration in gname_duration.items():
                for interval in duration:
                    objs.append(
                        user.Membership(user=u, group=g_d[gname],
                                        begins_at=interval.begin,
                                        ends_at=interval.end))

            try:
                ldap_account = resources['ldap_accounts'][_u.unix_account]
            except KeyError:
                continue

            if ldap_account.exaktiv:  # ex-aktiv
                objs.append(
                    user.Membership(user=u,
                                    group=g_d["org"],
                                    begins_at=u.registered_at,
                                    ends_at=u.registered_at+timedelta(days=1)))

            if ldap_account.aktiv:
                objs.append(
                    user.Membership(user=u,
                                    group=g_d['org'],
                                    begins_at=u.registered_at)
                )

    log.info("#fees {}".format((" ".join("{0}:{{{0}}}".format(key) for key in n.__dict__.keys())).format(**n.__dict__)))

    return objs
