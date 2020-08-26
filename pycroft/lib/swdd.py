import hmac
import os
import unicodedata
from enum import Enum
from typing import Optional

from sqlalchemy import func

from pycroft.model.swdd import Tenancy

swdd_hmac_key = os.environ.get('SWDD_HASH_KEY')


class TenancyStatus(Enum):
    PROVISIONAL = 1
    ESTABLISHED = 2


def get_swdd_person_id(first_name: str, last_name: str, birthdate: str) -> Optional[int]:
    """
    Builds a hmac hash from the given parameters and searches for a match in the Tenancy view

    :param first_name: The first name
    :param last_name: The last name
    :param birth_date: Date in ISO-8601
    :return: The person_id if found, else None
    """

    if swdd_hmac_key is None:
        raise ValueError("No hmac key set")

    digest_maker = hmac.new(swdd_hmac_key.encode(), digestmod="sha512")

    norm_str = unicodedata.normalize("NFC", "{}_{}_{}".format(first_name, last_name, birthdate)
                                                      .lower()).encode('utf-8')

    digest_maker.update(norm_str)

    person_hash = digest_maker.hexdigest().upper()

    return Tenancy.q.filter_by(person_hash=person_hash, status_id=TenancyStatus.ESTABLISHED.value).first()


def get_relevant_tenancies(person_id: int):
    return Tenancy.q.filter_by(person_id=person_id, status=TenancyStatus.ESTABLISHED.value)\
        .filter(Tenancy.mietende > func.now()).all()