# coding=utf-8
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from collections import Counter
import logging as std_logging
log = std_logging.getLogger('translate')
import operator
import re
from datetime import datetime, date, timedelta

from pycroft.helpers.interval import open, closedopen, closed, IntervalSet


sem_fee_re = re.compile(u"(Sems?e?ster|[Mm]ail|Email)(geb(ü|ue)hr(en)?|[Bb]eitrr?ag|account)?( (?P<stype>[WSws][Ss]) ?(?P<syear1>(20)?[0-9]{2})(/(?P<syear2>(20)?[0-9]{2}))?)?")
con_fee_re = re.compile(u"(Au?nschluss|Anmelde)geb(ü|ue)hr$")
late_fee_re = re.compile(u"([Vv]ers?s(ä|ae|a)u?mniss?|[Vv]ersp(ä|ae)tungs)geb(ü|ue)hr")


class MatchException(Exception):
    pass


def match_semester(date, semesters):
    # interval tree would be nicer
    sems = filter(lambda sem: date in sem, semesters)
    return sems[0]


def match_semester_re(match, semesters):
    stype = match.group('stype')
    if stype is None:
        return

    syear1 = match.group('syear1')
    #syear2 = match.group('syear2')

    if syear1 and len(syear1) == 2:
        syear1 = "20"+syear1
    #if syear2 and len(syear2) == 2:
    #    syear2 = "20"+syear2

    month = 10 if stype.lower() == "ws" else 4
    return next(s for s in semesters
                if (s.begins_on == date(day=1, month=month, year=int(syear1))))


def membership_from_fees(user, semesters, n):
    reg_date = user.registered_at
    sems_regular = []
    sems_reduced = []
    splits = sorted(user.account.splits,
                    key=operator.attrgetter('transaction.valid_on'))
    sem_fees = []; sem_fee_dates = []
    other_fees = []
    for split in splits:
        if split.amount > 0:  # fee
            match = sem_fee_re.match(split.transaction.description)
            if match:
                sem_fees.append((split, match))
                sem_fee_dates.append(split.transaction.valid_on)
            else:
                other_fees.append(split)

    for i_fee, (split, sem_fee_match) in enumerate(sem_fees):
        val_date = split.transaction.valid_on
        sem = None
        sem_date = match_semester(val_date, semesters)
        sem_grace = match_semester(val_date+sem_date.grace_period, semesters)
        sem_name = match_semester_re(sem_fee_match, semesters)

        first_fee = (i_fee == 0)
        more_fees_within_grace_time = (len(sem_fees)>1 and
                    sem_fees[1][0].transaction.valid_on == sem_grace.begins_on)

        try:
            # attempt to gauge best semester
            if sem_name == sem_date:
                if first_fee and sem_grace != sem_date:
                    if not more_fees_within_grace_time:
                        sem = sem_grace
                    else:
                        sem = sem_date
                else:
                    sem = sem_date

            else: # sem_date != sem_name and maybe sem_name = None
                if not first_fee:
                    if val_date == sem_date.begins_on:  # subsequent fee with wrong semester name
                        sem = sem_date

                    # fee for previous semester
                    elif sem_name and (val_date - sem_name.ends_on < timedelta(weeks=52/2) and
                      (split.amount == sem_name.reduced_semester_fee or "nachtra" in split.transaction.description.lower())):
                            sem = sem_name

                    else:
                        if sem_name:
                            raise MatchException("name!=date [subsequent fee]")
                        else:  # assume date is correct
                            sem = sem_date

                elif first_fee:
                    if abs((reg_date - val_date).days) > 1 and reg_date != datetime.fromtimestamp(0).date():
                        raise MatchException("first user fee is not on registration date, reg={}, first={}".format(reg_date, val_date))

                    if sem_name == sem_grace and not more_fees_within_grace_time: # within gracetime for next semester, name correct
                        # correctly named fee (grace)
                        sem = sem_name

                    elif len(sem_fees) > 1:
                        if more_fees_within_grace_time: #next fee is within grace period, i.e. no grace given
                            sem = sem_date
                        else: # next fee is not within grace period
                            sem = sem_grace

                    else: # user only has one semester fee, with name not matching date and name not matching semester within gracetime
                        if sem_name == None: # assume date is correct if fee is unnamed
                            sem = sem_date
                        else:
                            raise MatchException("too many unknowns [first&only fee]")

            if (split.amount == sem.regular_semester_fee or
                    split.amount == sem.regular_semester_fee + sem.late_fee):
                sems_regular.append(sem)
            elif split.amount == sem.reduced_semester_fee:
                sems_reduced.append(sem)
            else:
                raise MatchException("non-matching fee amount for sem "+sem.name)

        except MatchException as e:
            log.warning(u"failed: {}".format(e.message))
            n.failed += 1
        else:
            if sem == sem_name:
                n.ok += 1
            else:
                log.debug(u"using fix")
                n.fixed += 1

    for split in other_fees:
        desc = split.transaction.description
        if not con_fee_re.match(desc) and not late_fee_re.match(desc):
            if re.search(u"(kleidung|r(u|ue|ü)ck|ausgleich|spende)", desc,
                         flags=re.IGNORECASE|re.UNICODE):
                n.ignored += 1
            else:
                n.unclassified += 1
                log.warning(u"User {}: Unclassified user fee: {} {} {}".format(
                    user.id, desc, split.amount, split.transaction.id))

    # check if any semesters are used twice, meaning i probably made a mistake
    if len(set(sems_regular)) != len(sems_regular):
        log.warning(u"User {} overbilled for semesters {}".format(
            user.id,
            {k.name: v for k, v in Counter(sems_regular).items() if v != 1}))

    sem_to_interval = lambda s: closedopen(s.begins_on,
                                           s.ends_on+timedelta(days=1))
    regular_duration = sum(map(sem_to_interval, sems_regular), IntervalSet())
    reduced_duration = sum(map(sem_to_interval, sems_reduced), IntervalSet())

    # people that were away at some point, i.e. intervalset non-contiguous
    if len(regular_duration) > 1:
        end_to_end_regular_duration = IntervalSet(
            closedopen(regular_duration[0].begin, regular_duration[-1].end))

        # add reduced membership to people that returned (-> temporary leave)
        reduced_duration += end_to_end_regular_duration - regular_duration

        # add regular membership to people that returned (-> temporary leave)
        regular_duration = end_to_end_regular_duration

    # handle reconstructed deleted users
    if user.registered_at == datetime.fromtimestamp(0) and regular_duration:
        user.registered_at = datetime.combine(regular_duration[0].begin,
                                              datetime.min.time())

    # remove/add duration from registrations
    regular_duration -= IntervalSet(open(None, user.registered_at))
    if regular_duration:
        regular_duration += IntervalSet(closed(user.registered_at,
                                               regular_duration[0].begin))

    return regular_duration, reduced_duration
