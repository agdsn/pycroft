# Copyright (c) 2018 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from factory import SubFactory

from pycroft.model.config import Config
from .base import BaseFactory
from .finance import AccountFactory, BankAccountFactory
from .property import PropertyGroupFactory, MemberPropertyGroupFactory


class ConfigFactory(BaseFactory):
    """This is a dummy Config factory, Referencing PropertyGroups with
    no a-priori property relationships and arbitrary Accounts.
    """
    class Meta:
        model = Config

    id = 1

    # `PropertyGroup`s
    member_group = SubFactory(MemberPropertyGroupFactory)
    network_access_group = SubFactory(PropertyGroupFactory)
    violation_group = SubFactory(PropertyGroupFactory)
    traffic_limit_exceeded_group = SubFactory(PropertyGroupFactory)
    external_group = SubFactory(PropertyGroupFactory)
    payment_in_default_group = SubFactory(PropertyGroupFactory,
                                          name='Payment in default',
                                          granted=frozenset(("payment_in_default",)),
                                          denied=frozenset(("network_access", "userwww", "userdb")))
    blocked_group = SubFactory(PropertyGroupFactory)
    caretaker_group = SubFactory(PropertyGroupFactory)
    treasurer_group = SubFactory(PropertyGroupFactory)
    pre_member_group = SubFactory(PropertyGroupFactory)

    # `Account`s
    membership_fee_account = SubFactory(AccountFactory, type="REVENUE")
    membership_fee_bank_account = SubFactory(BankAccountFactory)
    non_attributable_transactions_account = SubFactory(AccountFactory, type="REVENUE")
