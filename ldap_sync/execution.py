#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""
ldap_sync.execution
~~~~~~~~~~~~~~~~~~~
Execution strategies for an :cls:`Action`.
Concretely, the real one and the dry-run.
"""
import functools
import logging

import ldap3

from ldap_sync.concepts.action import (
    Action,
    AddAction,
    DeleteAction,
    ModifyAction,
    IdleAction,
)


@functools.singledispatch
def execute_real(action: Action, connection: ldap3.Connection) -> None:
    raise TypeError(f"No dispatch defined for action of type {type(action).__name__}")


@execute_real.register
def _(action: AddAction, connection: ldap3.Connection) -> None:
    action.logger.debug("Executing %s for %s", type(action).__name__, action.record_dn)
    action.logger.debug("Attributes used: %s", action.nonempty_attrs)
    connection.add(action.record_dn, attributes=action.nonempty_attrs)
    debug_whether_success(action.logger, connection)


@execute_real.register
def _(action: ModifyAction, connection: ldap3.Connection) -> None:
    action.logger.debug(
        "Executing %s for %s (%s)",
        type(action).__name__,
        action.record_dn,
        ", ".join(action.modifications),
    )
    connection.modify(
        dn=action.record_dn,
        changes={
            # attention: new_value might be list!
            attr: (ldap3.MODIFY_REPLACE, new_value)
            for attr, new_value in action.modifications.items()
        },
    )
    debug_whether_success(action.logger, connection)


@execute_real.register
def _(action: DeleteAction, connection: ldap3.Connection) -> None:
    action.logger.debug("Executing %s for %s", type(action).__name__, action.record_dn)
    connection.delete(action.record_dn)
    debug_whether_success(action.logger, connection)


@execute_real.register
def _(action: IdleAction, connection: ldap3.Connection) -> None:
    pass


def debug_whether_success(logger: logging.Logger, connection: ldap3.Connection) -> None:
    """Communicate whether the last operation on `connection` has been successful."""
    if connection.result["result"]:
        logger.warning("Operation unsuccessful: %s", connection.result)
    else:
        logger.debug("Operation successful")
