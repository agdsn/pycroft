#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from __future__ import division, print_function
from collections import namedtuple
import csv
from datetime import datetime
from itertools import chain
import operator

from pycroft.lib.finance import (
    remove_keywords, tokenize, matches_by_uid_in_words,
    compute_matches_by_user_names_in_words,
    compute_optimal_match_ratio_munkres)


class NoMatch(Exception):
    pass


class MultipleMatches(Exception):
    pass


class NotBestMatch(Exception):
    pass


User = namedtuple('User', ['user_id','name_words'])


class Statistics(object):
    def __init__(self):
        self.matches = 0
        self.no_matches = 0
        self.not_best_matches = 0
        self.multiple_matches = 0

    def __str__(self):
        return "\n".join(
            attr + ": " + str(getattr(self, attr))
            for attr in ("matches", "no_matches", "not_best_matches", "multiple_matches")
        )


def decode_record(record):
    uid, first_name, last_name, date, amount, description = record
    return (
        int(uid),
        first_name.decode("utf-8"),
        last_name.decode("utf-8"),
        datetime.strptime(date, "%Y-%m-%d"),
        int(amount),
        description.decode("utf-8")
    )


def evaluate(found_users, expected_user, description, cleaned_description, tokenized_description, statistics):
    found_users.reverse()
    if expected_user not in map(operator.itemgetter(1), found_users):
        statistics.no_matches += 1
        raise NoMatch(
            u"NoMatch: found {} expected {} in:\n{}\n{}\n{}".format(
                found_users, expected_user,
                description, cleaned_description, tokenized_description
            )
        )

    if expected_user != found_users[0][1]:
        statistics.not_best_matches += 1
        raise NotBestMatch(
            u"NotBestMatch: found {} expected {} in:\n{}\n{}\n{}".format(
                found_users, expected_user,
                description, cleaned_description, tokenized_description
            )
        )
    if len(found_users) > 1:
        statistics.multiple_matches += 1
        raise MultipleMatches(
            u"MultipleMatches: found {} expected just {} in:\n{}\n{}\n{}".format(
                found_users, expected_user,
                description, cleaned_description, tokenized_description
            )
        )
    statistics.matches += 1


def print_exception(exception):
    print(unicode(exception).encode("utf-8"))


def main():
    with open('matched_payments.csv', 'rb') as csv_file:
        print("Reading users...")
        records = map(decode_record, csv.reader(csv_file))
        entries = 1000
        users = {
            uid: User(
                uid,
                tuple(chain(tokenize(first_name), tokenize(last_name))))
            for uid, first_name, last_name, date, amount, description
            in records[-entries:]}

        print("Starting matching...")
        uid_statistics = Statistics()
        name_statistics = Statistics()
        never_found = 0
        for uid, first_name, last_name, date, amount, description in records[-entries:]:
            cleaned_description = remove_keywords(description)
            tokenized_description = tokenize(cleaned_description)
            expected_user = users[uid]
            found_by_uid = matches_by_uid_in_words(tokenized_description, users)
            found_by_name = compute_matches_by_user_names_in_words(tokenized_description, users)
            matched = False
            try:
                evaluate(
                    found_by_uid, expected_user,
                    description, cleaned_description, tokenized_description,
                    uid_statistics
                )
            except (NoMatch, NotBestMatch) as e:
                pass
            except MultipleMatches as e:
                matched = True
                print_exception(e)
                print("")
            else:
                matched = True

            try:
                evaluate(
                    found_by_name, expected_user,
                    description, cleaned_description, tokenized_description,
                    name_statistics
                )
            except NoMatch as e:
                print_exception(e)
                print("Correct match had ratio {}".format(
                    compute_optimal_match_ratio_munkres(
                        expected_user.name_words, tokenized_description)
                    )
                )
                print("")
            except NotBestMatch as e:
                print_exception(e)
                print("")
            except MultipleMatches as e:
                matched = True
                #print_exception(e)
                #print("")
            else:
                matched = True
            if not matched:
                never_found += 1
        print("UID Matching:")
        print(uid_statistics)
        print("Name Matching:")
        print(name_statistics)
        print("Summary:")
        print("never_found: " + str(never_found))
        print("number_entries: " + str(entries))
        print("fail percentage: " + str(never_found / entries * 100))


if __name__ == "__main__":
    main()

