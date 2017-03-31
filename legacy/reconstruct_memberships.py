# coding=utf-8
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from collections import Counter, defaultdict
import logging as std_logging
log = std_logging.getLogger('import.translate')
import operator
import re
from datetime import datetime, date, timedelta
from tools import invert_dict

from pycroft.helpers.interval import (open, closedopen, closed, IntervalSet,
                                      NegativeInfinity, PositiveInfinity)


sem_fee_re = re.compile(u"(Sems?e?ster|[Mm]ail|Email)(geb(ü|ue)hr(en)?|[Bb]eitrr?ag|account)?( (?P<stype>[WSws][Ss]) ?(?P<syear1>(20)?[0-9]{2})(/(?P<syear2>(20)?[0-9]{2}))?)?")
con_fee_re = re.compile(u"(Au?nschluss|Anmelde)geb(ü|ue)hr$")
late_fee_re = re.compile(u"([Vv]ers?s(ä|ae|a)u?mniss?|[Vv]ersp(ä|ae)tungs)geb(ü|ue)hr")
fee_new_re = re.compile(u"Mitgliedsbeitrag (?P<year>[0-9]{4})-(?P<month>0?[1-9]|1[0-2])$")


class MatchException(Exception):
    pass


def interval_count(interval_list):
    counter = {
        IntervalSet(closedopen(NegativeInfinity, PositiveInfinity)): 0}
    for interval in interval_list:
        isect = {k: k & interval for k in counter if k & interval}
        for isected_interval in isect:
            previous_count = counter.pop(isected_interval)
            # intersecting part:
            counter[isect[isected_interval]] = previous_count + 1
            # non-intersecting parts:
            for interval_unchanged in (isected_interval -
                                           isect[isected_interval]):
                if interval_unchanged:
                    counter[IntervalSet(interval_unchanged)] = previous_count
    return counter


def monthdelta(date, delta):
     new_month = (date.month + delta - 1) % 12 + 1
     year_delta = (date.month + delta - new_month) / 12
     return date.replace(year=date.year+year_delta, month=new_month, day=1)


def sem_to_interval(s):
    return closedopen(s.begins_on, s.ends_on + timedelta(days=1))


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


def fee_semester_classifier(features):
    (val_date, sem_date, sem_grace, sem_name, is_first_fee,
    more_fees_within_grace_time, reg_date, split, sem_fees) = features
    if sem_name == sem_date:
        if (is_first_fee and sem_grace != sem_date and
                not more_fees_within_grace_time):
            return sem_grace, 1
        else:
            return sem_date, 3

    else:  # sem_date != sem_name and maybe sem_name = None
        if not is_first_fee:
            # subsequent fee with wrong semester name
            if val_date == sem_date.begins_on:
                return sem_date, 4

            # fee for previous semester
            elif (sem_name and
                  val_date - sem_name.ends_on < timedelta(weeks=52/2) and
                  (split.amount == sem_name.reduced_semester_fee or
                           "nachtra" in split.transaction.description.lower())):
                return sem_name, 5

            else:
                if sem_name:
                    raise MatchException("name!=date [subsequent fee]")
                else:  # assume date is correct
                    return sem_date, 6

        elif is_first_fee:
            if (abs((reg_date - val_date).days) > 1 and
                    reg_date != datetime.fromtimestamp(0).date()):
                raise MatchException(
                    "first user fee is not on registration date, "
                    "reg={}, first={}".format(reg_date, val_date))
            # within gracetime for next semester, name correct
            if sem_name == sem_grace and not more_fees_within_grace_time:
                # correctly named fee (grace)
                return sem_name, 7

            elif len(sem_fees) > 1:
                # next fee is within grace period, i.e. no grace given
                if more_fees_within_grace_time:
                    return sem_date, 8
                else:  # next fee is not within grace period
                    return sem_grace, 9

            # user only has one semester fee, with name not matching date and
            # name not matching semester within gracetime
            else:
                if sem_name == None:  # assume date is correct if fee is unnamed
                    return sem_date, 10
                else:
                    raise MatchException("too many unknowns [first&only fee]")
    return None, -1

def membership_from_fees(user, semesters, n):
    reg_date = user.registered_at
    intervals_regular = []
    intervals_reduced = []
    splits = sorted(user.account.splits,
                    key=operator.attrgetter('transaction.valid_on'))
    sem_fees = []; sem_fee_dates = []
    other_fees = []
    for split in splits:
        if split.amount > 0:  # fee
            match = (sem_fee_re.match(split.transaction.description) or
                     fee_new_re.match(split.transaction.description))
            if match:
                sem_fees.append((split, match))
                sem_fee_dates.append(split.transaction.valid_on)
            else:
                other_fees.append(split)

    for i_fee, (split, fee_match) in enumerate(sem_fees):

        if fee_match.re == fee_new_re:
            year = int(fee_match.group('year'))
            month = int(fee_match.group('month'))
            next_month = month % 12 + 1
            next_month_year = year + (month + 1 - next_month)/12
            month_interval = closedopen(
                date(year=year, month=month, day=1),
                date(year=next_month_year, month=next_month, day=1))
            intervals_regular.append(month_interval)
            n.ok += 1
            continue

        val_date = split.transaction.valid_on
        sem_date = match_semester(val_date, semesters)
        sem_grace = match_semester(val_date+sem_date.grace_period, semesters)
        sem_name = match_semester_re(fee_match, semesters)

        first_fee = (i_fee == 0)
        more_fees_within_grace_time = (len(sem_fees)>1 and
                    sem_fees[1][0].transaction.valid_on == sem_grace.begins_on)

        try:
            # attempt to gauge best semester
            sem, branch = fee_semester_classifier(features=(
                val_date, sem_date, sem_grace, sem_name, first_fee,
                more_fees_within_grace_time, reg_date, split, sem_fees))

            if (split.amount == sem.regular_semester_fee or
                    split.amount == sem.regular_semester_fee + sem.late_fee):
                intervals_regular.append(sem_to_interval(sem))
            elif split.amount == sem.reduced_semester_fee:
                intervals_reduced.append(sem_to_interval(sem))
            else:
                log.warning("non-matching fee amount ({}) for sem {} ({}/{}/{})."
                            " Trying discrete proportional fitting of 1..6 months."
                            .format(split.amount, sem.name, sem.regular_semester_fee,
                                    sem.reduced_semester_fee, sem.late_fee))
                if split.amount > sem.regular_semester_fee:
                    raise MatchException("Booked fee is higher than regular semester fee.")

                # Reconstruct to how many months the fee has ben
                # reduced proportionally by the head of finance:
                # amount / fee_per_month = amount * 6 / fee
                proportional_months = float(split.amount) * 6 / sem.regular_semester_fee
                if not proportional_months.is_integer():
                    raise MatchException(
                        "Proportional fit failed ({} vs. {} corresponds to {} months)"
                        .format(split.amount, sem.regular_semester_fee, proportional_months))
                num_months = int(proportional_months)
                log.debug("The manually awarded fee corresponds to %s months", num_months)

                uncropped_interval = sem_to_interval(sem)
                intervals_below = [i for i in intervals_regular if i <= uncropped_interval]
                intervals_above = [i for i in intervals_regular if i >= uncropped_interval]

                touching_above = min(intervals_above).meets(uncropped_interval) \
                                 if intervals_above else False
                touching_below = max(intervals_below).meets(uncropped_interval) \
                                 if intervals_below else False

                if touching_above and touching_below:
                    log.warning("Membership Intervals touch seamlessly above and below"
                                " despite reduced fee. Not cropping.")
                    cropped_interval = uncropped_interval
                elif touching_below:
                    log.debug("Membership intervals touch below, cropping above.")
                    new_upper_bound = monthdelta(uncropped_interval.end, -num_months)
                    cropped_interval = closedopen(uncropped_interval.begin, new_upper_bound)
                elif touching_above:
                    log.debug("Membership intervals touch above, cropping below.")
                    new_lower_bound = monthdelta(uncropped_interval.begin, num_months)
                    cropped_interval = closedopen(new_lower_bound, uncropped_interval.end)
                else:
                    log.debug("max below / min above: %s / %s",
                              max(intervals_below) if intervals_below else "-",
                              min(intervals_above) if intervals_above else "-")
                    raise MatchException("Interval with customly reduced fee booking is isolated."
                                         " Not fitting.")

                log.debug("cropped_interval: %s", cropped_interval)
                intervals_regular.append(cropped_interval)


            if sem is None:
                raise MatchException("logic error")
        except MatchException as e:
            log.error(u"failed: {} {} '{}' {}".format(
                split.transaction.id, val_date, split.transaction.description,
                e.message))
            n.failed += 1
        else:
            if sem == sem_name:
                n.ok += 1
            else:
                log.warn(u"Assuming tx {id} '{desc}' ({date}) is fee for "
                          u"{sem} ({branch})".format(
                    id=split.transaction.id,
                    desc=split.transaction.description,
                    date=val_date,
                    sem=sem.name,
                    branch=branch))
                n.fixed += 1

    for split in other_fees:
        desc = split.transaction.description
        if not con_fee_re.match(desc) and not late_fee_re.match(desc):
            if re.search(u"(kleidung|r(u|ue|ü)ck|ausgleich|spende)", desc,
                         flags=re.IGNORECASE|re.UNICODE):
                n.ignored += 1
            else:
                n.unclassified += 1
                log.warning(u"User {}: Unclassified fee: {} {} {}".format(
                    user.id, desc, split.amount, split.transaction.id))

    # check if any fee intervals overlap
    count_regular_duration = invert_dict(interval_count(intervals_regular))

    if any(count > 1 for count in count_regular_duration):
        log.warning(u"User {} overbilled for period {}".format(
            user.id,
            {str(sum(v, IntervalSet())): k
             for k, v in count_regular_duration.items() if k > 1}))

    regular_duration = sum(intervals_regular, IntervalSet())
    reduced_duration = sum(intervals_reduced, IntervalSet())

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
