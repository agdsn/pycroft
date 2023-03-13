#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import typing as t
import datetime
import logging
from itertools import chain
from typing import NamedTuple

from fints.client import FinTS3PinTanClient
from fints.models import SEPAAccount
from fints.segments.statement import HKKAZ5, HKKAZ6, HKKAZ7, HIKAZ5, HIKAZ6, HIKAZ7
from fints.utils import mt940_to_array
from mt940.models import Transaction as MT940Transaction

from pycroft.helpers.functional import extract_types

logger = logging.getLogger(__name__)


class StatementError(NamedTuple):
    statement: str
    error: str


def try_decode_response(
    resp: HIKAZ5 | HIKAZ6 | HIKAZ7,
) -> list[MT940Transaction] | StatementError:
    """Attempt to parse a FINTS response (“segment”)."""

    # Note: MT940 messages are encoded in the S.W.I.F.T character set,
    # which is a subset of ISO 8859. There are no character in it that
    # differ between ISO 8859 variants, so we'll arbitrarily chose 8859-1.
    decoded_statement = resp.statement_booked.decode("iso-8859-1")
    try:
        return t.cast(list[MT940Transaction], mt940_to_array(decoded_statement))
    except Exception as e:
        return StatementError(decoded_statement, str(e))


def decode_responses(
    responses: list,
) -> tuple[list[MT940Transaction], list[StatementError]]:
    segment_results, errors, rest = extract_types(
        (try_decode_response(resp) for resp in responses),
        list[MT940Transaction],
        StatementError,
    )
    assert not rest
    return [*chain(*segment_results)], errors


class FinTS3Client(FinTS3PinTanClient):
    def get_filtered_transactions(
        self,
        account: SEPAAccount,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
    ) -> tuple[list[MT940Transaction], list[StatementError]]:
        """Fetches the list of transactions of a bank account in a certain timeframe.

        MT940-Errors are caught and the statements containing them returned as
        a separate list.

        :param account: SEPA
        :param start_date: First day to fetch
        :param end_date: Last day to fetch
        :return: A tuple with list of mt940.models.Transaction objects and another
        list with tuples of mt940-data and error messages.
        """
        with self._get_dialog() as dialog:
            hkkaz = self._find_highest_supported_command(HKKAZ5, HKKAZ6, HKKAZ7)

            logger.info(f"Start fetching from {start_date} to {end_date}")
            statement, errors = self._fetch_with_touchdowns(
                dialog,
                lambda touchdown: hkkaz(
                    account=hkkaz._fields["account"].type.from_sepa_account(account),
                    all_accounts=False,
                    date_start=start_date,
                    date_end=end_date,
                    touchdown_point=touchdown,
                ),
                decode_responses,
                "HIKAZ",
            )
            logger.info("Fetching done.")

        logger.debug(f"Statement: {statement}")
        return statement, errors
