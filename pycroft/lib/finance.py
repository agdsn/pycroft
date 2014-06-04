# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from __future__ import division

from collections import namedtuple
import cStringIO
import csv
from datetime import datetime, date
from itertools import imap, chain
import operator
import re

import munkres
import Levenshtein
from sqlalchemy import func, between, Integer, cast
from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import NoResultFound

from pycroft.helpers.errorcode import Type1Code, Type2Code
from pycroft.lib.all import with_transaction
from pycroft.lib.config import config
from pycroft.lib.user import decode_type1_user_id, decode_type2_user_id
from pycroft.model import session
from pycroft.model.finance import Semester, FinanceAccount, Transaction, Split,\
    Journal, JournalEntry
from pycroft.helpers.interval import single, closed
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.functions import sign, least
from pycroft.model.user import User


def get_semester_for_date(target_date):
    """
    Get the semester which contains a given target date.
    :param date target_date: The date for which a corresponding semester should
    be found.
    :rtype: Semester
    :raises sqlalchemy.orm.exc.NoResultFound if no semester was found
    :raises sqlalchemy.orm.exc.MultipleResultsFound if multiple semester were
    found.
    """
    return Semester.q.filter(
        between(target_date, Semester.begin_date, Semester.end_date)
    ).one()


def get_current_semester():
    """
    Get the current semester.
    :rtype: Semester
    """
    return get_semester_for_date(date.today())


def get_registration_fee_account():
    return FinanceAccount.q.filter(
        FinanceAccount.id == config['finance']['registration_fee_account_id']
    ).one()


def get_semester_contribution_account():
    account_id = config['finance']['semester_contribution_account_id']
    return FinanceAccount.q.filter(
        FinanceAccount.id == account_id
    ).one()


@with_transaction
def simple_transaction(description, debit_account, credit_account, amount,
                       author, valid_date=None):
    """
    Posts a simple transaction.
    A simple transaction is a transaction that consists of exactly two splits,
    where one account is debited and another different account is credited with
    the same amount.
    The current system date will be used as transaction date, an optional valid
    date may be specified.
    :param unicode description: Description
    :param FinanceAccount debit_account: Debit (germ. Soll) account.
    :param FinanceAccount credit_account: Credit (germ. Haben) account
    :param int amount: Amount in Eurocents
    :param User author: User who created the transaction
    :param valid_date: Date, when the transaction should be valid. Current
    system date, if omitted.
    :type valid_date: date or None
    :rtype: Transaction
    """
    if valid_date is None:
        valid_date = date.today()
    new_transaction = Transaction(
        description=description,
        author=author,
        valid_date=valid_date)
    new_debit_split = Split(
        amount=-amount,
        account=debit_account,
        transaction=new_transaction)
    new_credit_split = Split(
        amount=amount,
        account=credit_account,
        transaction=new_transaction)
    session.session.add_all(
        [new_transaction, new_debit_split, new_credit_split]
    )
    return new_transaction


def setup_user_finance_account(new_user, processor):
    conf = config["finance"]
    current_semester = get_current_semester()
    format_args = {
        "user_id": new_user.id,
        "user_name": new_user.name,
        "semester": current_semester.name
    }
    new_finance_account = FinanceAccount(
        name=conf["user_finance_account_name"].format(**format_args),
        type="ASSET"
    )
    new_user.finance_account = new_finance_account
    session.session.add(new_finance_account)

    # Initial bookings
    simple_transaction(
        conf["registration_fee_description"].format(**format_args),
        get_registration_fee_account(), new_finance_account,
        current_semester.registration_fee, processor
    )
    simple_transaction(
        conf["semester_contribution_description"].format(**format_args),
        get_semester_contribution_account(), new_finance_account,
        current_semester.regular_semester_contribution, processor
    )


@with_transaction
def complex_transaction(description, author, splits, valid_date=None):
    if valid_date is None:
        valid_date = date.today()
    objects = []
    new_transaction = Transaction(
        description=description,
        author=author,
        valid_date=valid_date
    )
    objects.append(new_transaction)
    objects.extend(
        Split(amount=amount, account=account, transaction=new_transaction)
        for (account, amount) in splits
    )
    session.session.add_all(objects)


def transferred_amount(from_account, to_account, begin_date=None, end_date=None):
    """
    Determine how much has been transferred from one account to another in a
    given interval.

    A negative value indicates that more has been transferred from to_account
    to from_account than the other way round.

    The interval boundaries may be None, which indicates no lower and upper
    bound respectively.
    :param FinanceAccount from_account:
    :param FinanceAccount to_account:
    :param date|None begin_date: since when (inclusive)
    :param date|None end_date: till when (inclusive)
    :rtype: int
    """
    split1 = aliased(Split)
    split2 = aliased(Split)
    query = session.session.query(
        cast(func.sum(
            sign(split2.amount) *
            least(func.abs(split1.amount), func.abs(split2.amount))
        ), Integer)
    ).select_from(
        split1
    ).join(
        (split2, split1.transaction_id == split2.transaction_id)
    ).join(
        Transaction, split2.transaction_id == Transaction.id
    ).filter(
        split1.account == from_account,
        split2.account == to_account,
        sign(split1.amount) != sign(split2.amount)
    )
    if begin_date is not None and end_date is not None:
        query = query.filter(
            between(Transaction.valid_date, begin_date, end_date)
        )
    elif begin_date is not None:
        query = query.filter(Transaction.valid_date >= begin_date)
    elif end_date is not None:
        query = query.filter(Transaction.valid_date <= end_date)
    return query.scalar()


MT940_FIELDNAMES = [
    'our_account_number',
    'transaction_date',
    'valid_date',
    'type',
    'description',
    'other_name',
    'other_account_number',
    'other_routing_number',
    'amount',
    'currency',
    'info',
]


MT940Record = namedtuple("MT940Record", MT940_FIELDNAMES)


class MT940Dialect(csv.Dialect):
    delimiter = ";"
    quotechar = '"'
    doublequote = True
    skipinitialspace = True
    lineterminator = '\n'
    quoting = csv.QUOTE_ALL


class CSVImportError(Exception):

    def __init__(self, message, cause=None):
        if cause is not None:
            message = message + u" caused by " + repr(cause)
        super(CSVImportError, self).__init__(message, cause)
        self.cause = cause


def import_journal_csv(csv_file, import_time=None):
    if import_time is None:
        import_time = datetime.utcnow()

    # Convert to MT940Record and enumerate
    reader = csv.DictReader(csv_file, MT940_FIELDNAMES, dialect=MT940Dialect)
    records = enumerate(imap(lambda r: MT940Record(**r), reader), 1)
    # Skip first record (header)
    try:
        records.next()
    except StopIteration:
        raise CSVImportError(u"Leerer Datensatz.")

    session.session.add_all(imap(
        lambda r: process_record(r[0], r[1], import_time),
        reversed(list(records))
    ))
    session.session.commit()


def remove_space_characters(field):
    """Remove every 28th character if it is a space character."""
    if field is None:
        return None
    characters = filter(
        lambda c: (c[0] + 1) % 28 != 0 or c[1] != u' ',
        enumerate(field)
    )
    return u"".join(map(lambda c: c[1], characters))


# Banks are using the original description field to store several subfields with
# SEPA. Subfields start with a four letter tag name and the plus sign, they
# are separated by space characters.
sepa_description_field_tags = (
    u'EREF', u'KREF', u'MREF', u'CRED', u'DEBT', u'SVWZ', u'ABWA', u'ABWE'
)
sepa_description_pattern = re.compile(r''.join(chain(
    ur'^',
    map(
        lambda tag: ur'(?:({0}\+.*?)(?: (?!$)|$))?'.format(tag),
        sepa_description_field_tags
    ),
    ur'$'
)), re.UNICODE)


def cleanup_description(description):
    match = sepa_description_pattern.match(description)
    if match is None:
        return description
    return u' '.join(map(
        remove_space_characters,
        filter(
            lambda g: g is not None,
            match.groups()
        )
    ))


def restore_record(record):
    string_buffer = cStringIO.StringIO()
    csv.DictWriter(
        string_buffer, MT940_FIELDNAMES, dialect=MT940Dialect
    ).writerow(record._asdict())
    restored_record = string_buffer.getvalue()
    string_buffer.close()
    return restored_record


def process_record(index, record, import_time):
    if record.currency != u"EUR":
        message = u"Nicht unterstützte Währung {0} in Datensatz {1}: {2}"
        raw_record = restore_record(record)
        raise CSVImportError(
            message.format(record.currency, index, raw_record)
        )
    try:
        journal = Journal.q.filter_by(
            account_number=record.our_account_number
        ).one()
    except NoResultFound as e:
        message = u"Kein Journal mit der Kontonummer {0} gefunden."
        raise CSVImportError(message.format(record.our_account_number), e)

    try:
        valid_date = datetime.strptime(record.valid_date, u"%d.%m.%y").date()
        transaction_date = (datetime
                            .strptime(record.transaction_date, u"%d.%m")
                            .date())
    except ValueError as e:
        message = u"Unbekanntes Datumsformat in Datensatz {0}: {1}"
        raw_record = restore_record(record)
        raise CSVImportError(message.format(index, raw_record), e)

    # Assume that transaction_date's year is the same
    transaction_date = transaction_date.replace(year=valid_date.year)
    # The transaction_date may not be after valid_date, if it is, our
    # assumption was wrong
    if transaction_date > valid_date:
        transaction_date = transaction_date.replace(
            year=transaction_date.year - 1
        )
    return JournalEntry(
        amount=int(record.amount.replace(u",", u"")),
        journal=journal,
        description=cleanup_description(record.description),
        original_description=record.description,
        other_account_number=record.other_account_number,
        other_routing_number=record.other_routing_number,
        other_name=record.other_name,
        import_time=import_time,
        transaction_date=transaction_date,
        valid_date=valid_date
    )


keyword_pattern = re.compile(
    ur'(Nutzer[\s\-]ID'
    ur'|AG\s?DSN'
    ur'|Wundt\s?str(?:a(?:ss|ß)e|\.)?\s?(?:11|1|3|5|7|9)?'
    ur'|Zellescher\s?Weg\s?41\s?[abcd]?'
    ur'|ZW\s?41[abcd]?'
    ur')',
    re.UNICODE | re.IGNORECASE | re.VERBOSE
)


tokenize_pattern = re.compile(
    ur"""
        (?:
        [\s\+\.,;/]              # Whitespace and punctuation
        |(?<![0-9])-(?![0-9])   # Dash not enclosed by numbers
        |(?<=[a-z]{2})(?=[A-Z]) # Case change inside word
        |(?<=[0-9])(?=[a-zA-Z]) # Number inside word
        )+                      # Repeat everything
    """,
    re.UNICODE | re.VERBOSE
)


def remove_keywords(string):
    """
    Remove certain keywords from a description.

    Must be applied before tokenization as this function is white space aware.
    :param unicode string: bank transfer description
    :rtype: unicode
    """
    match = sepa_description_pattern.search(string)
    if match:
        # Remove the 5 leading characters, because they are SEPA description
        # field tags
        string = u' '.join(
            group[5:] for group in match.groups() if group is not None
        )    
    return keyword_pattern.sub(" ", string)


def tokenize(string):
    """
    Split a string on whitespace, punctuation or lower to upper case change
    into tokens.
    :param unicode string: a character string
    :rtype: list[unicode]
    """
    #print string.decode("utf-8")
    return tokenize_pattern.sub(" ", string).lower().strip().split()



def match_entries(entries, users_db):
    """
    
    """
    matched_entries = list()
    users = {user.id: User(user.id, tokenize(user.name)) for user in users_db}
    for entry in entries:
        a = match_entry(entry,users)
        map(lambda ratio,user:(ratio,users_db.find(user[0])
            matched_entries.append((entry,match_entry(entry,users)))))
    return matched_entries

def match_entry(entry,users):    
    """
    Tries to match a payment entry with a user.
    :param JournalEntry entry: a journal entry
    :param User:
    :rtype: list[(float, int)] 
    """
    
    if entry.amount < 0:
        return []
    tokenized_description = tokenize(remove_keywords(entry.descrption))
    tokenized_other_name =   tokenize(remove_keywords(entry.other_name)) 
    matched_users = []
    matched_users.extend(compute_matches_by_uid_in_words(tokenized_description, users))
    matched_users.extend(compute_matches_by_user_names_in_words(tokenized_other_name, users))
    matched_users.extend(compute_matches_by_user_names_in_words(
        tokenized_description, 
        users
    ))
    return combine_matches(matched_users)


def combine_matches(*user_matches):
    sorted(chain(*user_matches), reverse=True)
    no_double_entries = []
    found_uids = set()
    for ratio,user in user_matches:
        if user.id in found_uids:
            continue
        found_uids.add(user.id)
        no_double_entries.append((ratio,user))
    return no_double_entries
            

def compute_matches_by_uid_in_words(words, users):
    """
    :param iterable[unicode] words: a list of words
    :param dict[int, User] users: a map from uid to user
    :rtype: list[(float, User)]
    """
    matched_users = set()
    for word in words:
        decoded = decode_type1_user_id(word)
        if decoded and Type1Code.is_valid(*decoded):
            user_id, _ = decoded
            if user_id in users:
                matched_users.add((1.0, users[user_id]))
        decoded = decode_type2_user_id(word)
        if decoded and Type2Code.is_valid(*decoded):
            user_id, _ = decoded
            if user_id in users:
                matched_users.add((1.0, users[user_id]))
    return list(matched_users)


def compute_greedy_match_ratio(required_words, sample_words):
    """
    Compute the best match ratio greedily. Find the best matching sample word
    for each required word and then compute the length-weighted average over
    all the match ratios. Use the length of the required words for
    length-weighting.

    While this is a good approximation to the optimal match ratio, it's very
    bad in certain cases. Consider the required words ["Lang", "Lang"] and the
    sample words ["Christian", "Lang"], the greedy match would return 1.0,
    although only one of the required words has actually been matched. For this
    very reason this function will return None in this case.
    :param sequence[unicode] required_words: required words
    :param sequence[unicode] sample_words: sample words
    :returns: ratio between 0.0 and 1.0 indicating how much of the required
    words was matched by the sample words or None if a greedy match would be
    incorrect
    :rtype: float|None
    """
    total_rws_len = sum(imap(len, required_words))
    total_sws_len = sum(imap(len, sample_words))
    if total_rws_len == 0 or total_sws_len == 0:
        return 0.0
    rws_count = len(required_words)
    sws_count = len(sample_words)
    matches = list()
    for rw_index, rw in enumerate(required_words):
        # Determine best matching sample word for the required word
        sw_index, ratio = max(
            ((sw_index, Levenshtein.ratio(rw, sw))
             for sw_index, sw in enumerate(sample_words)),
            key=operator.itemgetter(1)
        )
        matches.append((rw_index, sw_index, ratio * len(rw)))
    # Select the best matches if less required words than sample words
    matches.sort(key=operator.itemgetter(2), reverse=True)
    matches = matches[:min(rws_count, sws_count)]
    # Check for duplicate sample word matches
    if len(set(imap(operator.itemgetter(1), matches))) != len(matches):
        return None
    ratio_sum = sum(imap(operator.itemgetter(2), matches))
    return ratio_sum/total_rws_len


def compute_optimal_match_ratio_munkres(required_words, sample_words):
    """
    Compute the optimal matching ratio between the required words and the sample
    words, where each required word may match only one sample word, and each
    sample word may match only one required word, i.e. solve a linear assignment
    problem.

    The resulting ratio is the length-weighted average of the single match
    ratios. It is length-weighted with regard to the required word length.
    :param iterable[unicode] required_words: required words
    :param iterable[unicode] sample_words: sample words
    :returns: ratio between 0.0 and 1.0 indicating how much of the required
    words was matched by the sample words
    :rtype: float
    """
    total_rws_len = sum(imap(len, required_words))
    total_sws_len = sum(imap(len, sample_words))
    if total_rws_len == 0 or total_sws_len == 0:
        return 0.0
    dim = min(len(required_words), len(sample_words))
    # Compute the cost for each pair of required and sample word
    cost_matrix = [
        [total_rws_len - (len(rw) * Levenshtein.ratio(rw, sw))
         for sw in sample_words]
        for rw in required_words
    ]
    lap_solver = munkres.Munkres()
    indices = lap_solver.compute(cost_matrix)
    cost_sum = sum(cost_matrix[row][column] for row, column in indices)
    return dim - cost_sum/total_rws_len


def adaptive_match_ratio(required_words, sample_words):
    """
    Compute the optimal matching ratio adaptively using greedy matching if the
    required words are not very similar else use the correct, but more expensive
    linear assignment problem computation.
    """
    ratio = compute_greedy_match_ratio(required_words, sample_words)
    if ratio is not None:
        return ratio
    else:
        return compute_optimal_match_ratio_munkres(required_words, sample_words)


def compute_matches_by_user_names_in_words(words, users, threshold=0.8):
    """
    :param sequence[unicode] words:
    :param dict[int, User] users:
    :rtype: list[(float, User)]
    """
    matched_users = []
    for user in users.itervalues():
        ratio = adaptive_match_ratio(user.name_words, words)
        if ratio > threshold:
            matched_users.append((ratio, user))
    matched_users.sort()
    return matched_users

