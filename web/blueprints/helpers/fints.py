import datetime
import logging
from fints.client import FinTS3PinTanClient
from fints.models import SEPAAccount
from fints.segments.statement import HKKAZ5, HKKAZ6, HKKAZ7
from fints.utils import mt940_to_array

logger = logging.getLogger(__name__)

class FinTS3Client(FinTS3PinTanClient):

    def get_filtered_transactions(self, account: SEPAAccount,
                         start_date: datetime.date = None,
                         end_date: datetime.date = None):
        """
        Fetches the list of transactions of a bank account in a certain timeframe.
        MT940-Errors are catched and the statements containing them returned as
        a seperate list.

        :param account: SEPA
        :param start_date: First day to fetch
        :param end_date: Last day to fetch
        :return: A tuple with list of mt940.models.Transaction objects and another
        list with tuples of mt940-data and error messages.
        """

        with self._get_dialog() as dialog:
            hkkaz = self._find_highest_supported_command(HKKAZ5, HKKAZ6, HKKAZ7)

            logger.info(
                'Start fetching from {} to {}'.format(start_date, end_date))
            responses = self._fetch_with_touchdowns(
                dialog,
                lambda touchdown: hkkaz(
                    account=hkkaz._fields['account'].type.from_sepa_account(
                        account),
                    all_accounts=False,
                    date_start=start_date,
                    date_end=end_date,
                    touchdown_point=touchdown,
                ),
                'HIKAZ'
            )
            logger.info('Fetching done.')

        statement = []
        with_error = []
        for seg in responses:
            # Note: MT940 messages are encoded in the S.W.I.F.T character set,
            # which is a subset of ISO 8859. There are no character in it that
            # differ between ISO 8859 variants, so we'll arbitrarily chose 8859-1.
            try:
                statement += mt940_to_array(
                    seg.statement_booked.decode('iso-8859-1'))
            except Exception as e:
                with_error.append((seg.statement_booked.decode('iso-8859-1'), str(e)))

        logger.debug('Statement: {}'.format(statement))


        return statement, with_error
