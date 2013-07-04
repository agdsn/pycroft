# Copyright (c) 2013 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.model import session

_transactions = []


def with_transaction(func):
    def helper(*args, **kwargs):
        if not _transactions:
            transaction = session.session
        else:
            transaction = session.session.begin(subtransactions=True)

        _transactions.append(transaction)
        try:
            ret = func(*args, **kwargs)
            transaction.commit()
        except Exception, e:
            transaction.rollback()
            raise e
        finally:
            _transactions.pop()

        return ret

    return helper
