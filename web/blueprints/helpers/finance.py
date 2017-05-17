from pycroft.model.finance import Split, Transaction


def build_transactions_query(account, search=None, sort_by='valid_on', sort_order=None,
                             offset=None, limit=None, positive=None):
    """Build a query returning the Splits for a finance account

    :param Account account: The finance Account to filter by
    :param str search: The string to be included, insensitive
    :param str sort_by: The column to sort by.  Must be a column of
        :cls:`Transaction` or :cls:`Split`.
    :param str sort_order: Trigger descending sort order if the value
        is ``'desc'``.  See also the effect of :attr:`positive`.
    :param int offset:
    :param int limit:
    :param bool positive: if positive is set to ``True``, only get
        splits with amount ≥ 0, and amount < 0 if ``False``.  In the
        latter case, the effect of the :attr:`sort_order` parameter is
        being reversed.

    :returns: The prepared SQLAlchemy query

    :rtype: Query
    """
    query = Split.q.join(Transaction).filter(Split.account == account)

    if not (sort_by in Transaction.__table__.columns
            or sort_by in Split.__table__.columns):
        sort_by = "valid_on"

    descending = (sort_order == "desc") ^ (positive == False)
    ordering = sort_by+" desc" if descending else sort_by
    if search:
        query = query.filter(Transaction.description.ilike('%{}%'.format(search)))

    if positive is not None:
        if positive:
            query = query.filter(Split.amount >= 0)
        else:
            query = query.filter(Split.amount < 0)

    query = query.order_by(ordering).offset(offset).limit(limit)

    return query
