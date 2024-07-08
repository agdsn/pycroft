from __future__ import annotations
import typing as t
from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    LargeBinary,
    Sequence,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from pycroft.model import ddl
from pycroft.model.base import ModelBase, IntegerIdModel

# needed because the consistency trigger depends on the the `User` table
from .user import User


if t.TYPE_CHECKING:
    # FKeys

    # Backrefs
    pass


manager = ddl.DDLManager()
unix_account_uid_seq = Sequence("unix_account_uid_seq", start=1000, metadata=ModelBase.metadata)


class UnixAccount(IntegerIdModel):
    uid: Mapped[int] = mapped_column(
        ForeignKey("unix_tombstone.uid", deferrable=True),
        unique=True,
        server_default=unix_account_uid_seq.next_value(),
    )
    tombstone: Mapped[UnixTombstone] = relationship(viewonly=True)
    gid: Mapped[int] = mapped_column(default=100)
    login_shell: Mapped[str] = mapped_column(default="/bin/bash")
    home_directory: Mapped[str] = mapped_column(unique=True)


class UnixTombstone(ModelBase):
    # mapped_column does not work yet for reference in `__mapper_args__`, unfortunately.
    from sqlalchemy import Integer, String

    uid: Mapped[int] = Column(Integer, unique=True)
    login_hash: Mapped[bytes] = Column(LargeBinary(512), unique=True)

    # backrefs
    unix_account: Mapped[UnixAccount] = relationship(viewonly=True, uselist=False)
    # /backrefs

    __table_args__ = (
        UniqueConstraint("uid", "login_hash"),
        Index("uid_only_unique", login_hash, unique=True, postgresql_where=uid.is_(None)),
        Index(
            "login_hash_only_unique",
            uid,
            unique=True,
            postgresql_where=login_hash.is_(None),
        ),
        CheckConstraint("uid is not null or login_hash is not null"),
    )
    __mapper_args__ = {"primary_key": (uid, login_hash)}  # fake PKey for mapper


check_unix_tombstone_lifecycle_func = ddl.Function(
    name="check_unix_tombstone_lifecycle",
    arguments=[],
    rtype="trigger",
    definition="""
    BEGIN
        IF (NEW.login_hash IS NULL AND OLD.login_hash IS NOT NULL) THEN
            RAISE EXCEPTION 'Removing login_hash from tombstone is invalid'
                USING ERRCODE = 'check_violation';
        END IF;
        IF (NEW.uid IS NULL AND OLD.uid IS NOT NULL) THEN
            RAISE EXCEPTION 'Removing uid from tombstone is invalid'
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END;
    """,
    volatility="stable",
    language="plpgsql",
)
manager.add_function(UnixTombstone.__table__, check_unix_tombstone_lifecycle_func)
manager.add_trigger(
    UnixTombstone.__table__,
    ddl.Trigger(
        name="check_unix_tombstone_lifecycle_trigger",
        table=UnixTombstone.__table__,
        events=("UPDATE",),
        function_call=f"{check_unix_tombstone_lifecycle_func.name}()",
        when="BEFORE",
    ),
)

# unix account creation
manager.add_function(
    User.__table__,
    ddl.Function(
        "unix_account_ensure_tombstone",
        [],
        "trigger",
        # IF unix_account has a corresponding user
        # THEN use that tombstone.
        # However, in the scenario where the user's tombstone exists and points to a different uid,
        # we throw an error instead.
        """
        DECLARE
          v_user "user";
          v_login_ts unix_tombstone;
          v_ua_ts unix_tombstone;
        BEGIN
          select * into v_user from "user" u where u.unix_account_id = NEW.id;
          select * into v_ua_ts from unix_tombstone ts where ts.uid = NEW.uid;

          select ts.* into v_login_ts from "user" u
              join unix_tombstone ts on u.login_hash = ts.login_hash
              where u.unix_account_id = NEW.id;

          -- scenarios:
          -- 1) no user, no tombstone
          -- 2) no user, tombstone
          -- 3) user, no tombstone -> create
          -- 4) user + tombstone

          IF v_user IS NULL THEN
              IF v_ua_ts IS NULL THEN
                  insert into unix_tombstone (uid) values (NEW.uid);
              END IF;
              RETURN NEW;
          END IF;
          -- else: user not null
          IF v_ua_ts IS NULL THEN
              insert into unix_tombstone (uid, login_hash) values (NEW.uid, v_user.login_hash);
          END IF;

          RETURN NEW;
        END;
        """,
        volatility="volatile",
        strict=True,
        language="plpgsql",
    ),
)

manager.add_trigger(
    User.__table__,
    ddl.Trigger(
        "unix_account_ensure_tombstone_trigger",
        UnixAccount.__table__,
        ("INSERT",),
        "unix_account_ensure_tombstone()",
        when="BEFORE",
    ),
)

ensure_tombstone = ddl.Function(
    "user_ensure_tombstone",
    [],
    "trigger",
    # This function ensures satisfaction of the user → tombstone foreign key constraint
    #  (a "tuple generating dependency") which says ∀u: user ∃t: tombstone: t.login_hash = u.login_hash.
    # it does _not_ enforce the consistency constraint ("equality generating dependency").
    """
    DECLARE
      v_ua unix_account;
      v_login_ts unix_tombstone;
      v_ua_ts unix_tombstone;
      v_u_login_hash bytea;
    BEGIN
      select * into v_ua from unix_account ua where ua.id = NEW.unix_account_id;
      -- hash not generated yet, because we are a BEFORE trigger!
      select digest(NEW.login, 'sha512') into v_u_login_hash;

      select ts.* into v_login_ts from "user" u
          join unix_tombstone ts on v_u_login_hash = ts.login_hash
          where u.id = NEW.id;

      IF v_ua IS NULL THEN 
          IF v_login_ts IS NULL THEN
              -- TODO check whether this was a _set_ or an _update_.
              -- do we really want to automatically update this?
              -- NOTE: when an update caused this, this might create an inconsistent state (different tombstones for uid and login),
              --  however as soon as the check constraint fires the transaction will be aborted, anyway.
              insert into unix_tombstone (uid, login_hash) values (null, v_u_login_hash) on conflict do nothing;
          END IF;
          -- ELSE: user tombstone exists, no need to do anything
      ELSE
          select * into v_ua_ts from unix_tombstone ts where ts.uid = v_ua.uid;
          IF v_ua_ts.login_hash IS NULL THEN 
              update unix_tombstone ts set login_hash = v_u_login_hash where ts.uid = v_ua_ts.uid;
          END IF;
      END IF;

      RETURN NEW;
    END;
    """,
    volatility="volatile",
    strict=True,
    language="plpgsql",
)

manager.add_function(User.__table__, ensure_tombstone)

manager.add_trigger(
    User.__table__,
    ddl.Trigger(
        "user_ensure_tombstone_trigger",
        User.__table__,
        # TODO create different trigger on UPDATE which only fires if login or unix_account has changed
        ("INSERT", "UPDATE OF unix_account_id, login"),
        "user_ensure_tombstone()",
        when="BEFORE",
    ),
)

check_tombstone_consistency = ddl.Function(
    name="check_tombstone_consistency",
    arguments=[],
    rtype="trigger",
    definition="""
    DECLARE
        v_user "user";
        v_ua unix_account;
        v_user_ts unix_tombstone;
        v_ua_ts unix_tombstone;
    BEGIN
        IF TG_TABLE_NAME = 'user' THEN
            v_user := NEW;
            select * into v_ua from unix_account where unix_account.id = NEW.unix_account_id;
        ELSIF TG_TABLE_NAME = 'unix_account' THEN 
            v_ua := NEW;
            select * into v_user from "user" u where u.unix_account_id = NEW.id;
        ELSE
            RAISE EXCEPTION
                'trigger can only be invoked on user or unix_account tables, not %%',
                TG_TABLE_NAME
            USING ERRCODE = 'feature_not_supported';
        END IF;

        IF v_ua IS NULL OR v_user IS NULL THEN
            RETURN NEW; -- no consistency to satisfy
        END IF;
        ASSERT NOT v_user IS NULL, 'v_user is null!';
        ASSERT NOT v_user.login IS NULL, format('user.login is null (%%s): %%s (type %%s)', v_user.login, v_user, pg_typeof(v_user));

        select * into v_user_ts from unix_tombstone ts where ts.login_hash = v_user.login_hash;
        select * into v_ua_ts from unix_tombstone ts where ts.uid = v_ua.uid;

        -- this should already be ensured by the `ensure_*_tombstone` triggers,
        -- but we are defensive here to ensure consistency no matter what
        IF v_ua_ts IS NULL THEN
            ASSERT NOT v_ua IS NULL, 'unix_account is null';
            RAISE EXCEPTION
                'unix account with id=%% (uid=%%) has no tombstone.', v_ua.id, v_ua.uid
            USING ERRCODE = 'foreign_key_violation';
        END IF;
        IF v_user_ts IS NULL THEN
            RAISE EXCEPTION
                'user %% with id=%% (login=%%) has no tombstone.', v_user, v_user.id, v_user.login
            USING ERRCODE = 'foreign_key_violation';
        END IF;

        if v_user_ts <> v_ua_ts THEN
            RAISE EXCEPTION
                'User tombstone (uid=%%, login_hash=%%) and unix account tombstone (uid=%%, login_hash=%%) differ!',
                v_user_ts.uid, v_user_ts.login_hash, v_ua_ts.uid, v_ua_ts.login_hash
            USING ERRCODE = 'check_violation';
        END IF;

        RETURN NEW;
    END;
    """,
    strict=True,
    language="plpgsql",
)
manager.add_function(User.__table__, check_tombstone_consistency)
manager.add_constraint_trigger(
    User.__table__,
    ddl.ConstraintTrigger(
        name="user_check_tombstone_consistency_trigger",
        table=User.__table__,
        events=("INSERT", "UPDATE OF unix_account_id, login"),
        function_call=f"{check_tombstone_consistency.name}()",
        deferrable=True,
    ),
)
manager.add_constraint_trigger(
    # function needs user table
    User.__table__,
    ddl.ConstraintTrigger(
        name="unix_account_check_tombstone_consistency_trigger",
        table=UnixAccount.__table__,
        events=("INSERT", "UPDATE OF uid"),
        function_call=f"{check_tombstone_consistency.name}()",
        deferrable=True,
    ),
)
manager.register()
