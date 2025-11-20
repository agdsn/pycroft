"""Add UnixTombstone

Revision ID: 5234d7ac2b4a
Revises: bc0e0dd480d4
Create Date: 2024-09-09 08:17:24.686578

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "5234d7ac2b4a"
down_revision = "bc0e0dd480d4"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("create extension if not exists pgcrypto"))
    op.create_table(
        "unix_tombstone",
        sa.Column("uid", sa.Integer(), nullable=True),
        sa.Column("login_hash", sa.LargeBinary(length=512), nullable=True),
        sa.CheckConstraint("uid is not null or login_hash is not null"),
        sa.UniqueConstraint("login_hash"),
        sa.UniqueConstraint("uid"),
        sa.UniqueConstraint("uid", "login_hash"),
    )
    op.create_index(
        "login_hash_only_unique",
        "unix_tombstone",
        ["uid"],
        unique=True,
        postgresql_where=sa.text("login_hash IS NULL"),
    )
    op.create_index(
        "uid_only_unique",
        "unix_tombstone",
        ["login_hash"],
        unique=True,
        postgresql_where=sa.text("uid IS NULL"),
    )
    op.add_column(
        "pre_member",
        sa.Column(
            "login_hash",
            sa.LargeBinary(length=512),
            sa.Computed("digest(login, 'sha512')"),
            nullable=True,
        ),
    )

    op.execute(
        """
            insert into unix_tombstone (uid, login_hash)
            select ua.uid, digest(u.login, 'sha512')
            from "user" u full join unix_account ua on u.unix_account_id=ua.id;           
        """
    )

    op.create_foreign_key(None, "unix_account", "unix_tombstone", ["uid"], ["uid"], deferrable=True)
    # NOTE: pre_member does not actually have an FKey to unix_tombstone!
    # The col is there nonetheless.
    op.add_column(
        "user",
        sa.Column(
            "login_hash",
            sa.LargeBinary(length=512),
            sa.Computed("digest(login, 'sha512')"),
            nullable=True,
        ),
    )
    # This changes user → unix_account to `ON DELETE SET NULL`
    op.drop_constraint("user_unix_account_id_fkey", "user", type_="foreignkey")
    op.create_foreign_key(
        "user_unix_account_id_fkey",
        "user",
        "unix_account",
        ["unix_account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # /

    op.create_foreign_key(
        "user_login_hash_fkey",
        "user",
        "unix_tombstone",
        ["login_hash"],
        ["login_hash"],
        deferrable=True,
    )

    connection = op.get_bind()
    connection.execute(sa.text(SQL_TRIGGERS_CREATE))


def downgrade():
    op.drop_constraint("user_login_hash_fkey", "user", type_="foreignkey")
    op.drop_constraint("unix_account_uid_fkey", "unix_account", type_="foreignkey")

    op.drop_constraint("user_unix_account_id_fkey", "user", type_="foreignkey")
    op.create_foreign_key(
        "user_unix_account_id_fkey", "user", "unix_account", ["unix_account_id"], ["id"]
    )

    op.drop_column("user", "login_hash")
    op.drop_column("pre_member", "login_hash")
    op.drop_index(
        "uid_only_unique", table_name="unix_tombstone", postgresql_where=sa.text("uid IS NULL")
    )
    op.drop_index(
        "login_hash_only_unique",
        table_name="unix_tombstone",
        postgresql_where=sa.text("login_hash IS NULL"),
    )
    op.drop_table("unix_tombstone")

    connection = op.get_bind()
    connection.execute(sa.text(SQL_TRIGGERS_DROP))


# > from pycroft.model import unix_account as ua
# > from tests.model.ddl import literal_compile
# > print("\n".join(literal_compile(c).replace("%%", "%") for _, c, d in ua.manager.objects))
SQL_TRIGGERS_CREATE = """
CREATE OR REPLACE FUNCTION check_unix_tombstone_lifecycle() RETURNS trigger STABLE LANGUAGE plpgsql AS $$
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
$$;
CREATE TRIGGER check_unix_tombstone_lifecycle_trigger BEFORE UPDATE ON unix_tombstone FOR EACH ROW EXECUTE PROCEDURE check_unix_tombstone_lifecycle();
CREATE OR REPLACE FUNCTION unix_account_ensure_tombstone() RETURNS trigger VOLATILE STRICT LANGUAGE plpgsql AS $$
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

  IF v_user IS NULL THEN
      IF v_ua_ts IS NULL THEN
          insert into unix_tombstone (uid) values (NEW.uid);
      END IF;
      RETURN NEW;
  END IF;
  -- NOTE: v_user not null implies that we are in an UPDATE, not a CREATE,
  -- because otherwise it would be impossible for an existing user to reference this UA.

  IF v_ua_ts IS NULL THEN
      insert into unix_tombstone (uid, login_hash) values (NEW.uid, v_user.login_hash);
  END IF;

  RETURN NEW;
END;
$$;
CREATE TRIGGER unix_account_ensure_tombstone_trigger BEFORE INSERT ON unix_account FOR EACH ROW EXECUTE PROCEDURE unix_account_ensure_tombstone();
CREATE OR REPLACE FUNCTION user_ensure_tombstone() RETURNS trigger VOLATILE STRICT LANGUAGE plpgsql AS $$
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

  IF TG_OP = 'INSERT' THEN
      IF not v_login_ts IS NULL THEN
          RAISE EXCEPTION
              'User with login=% already exists. Please choose a different login.',
              NEW.login
              USING ERRCODE = 'foreign_key_violation';
      END IF;

      IF v_ua IS NULL THEN
          insert into unix_tombstone (uid, login_hash) values (null, v_u_login_hash);
          -- on conflict: raise! want to prohibit re-use after all.
      ELSE
          IF v_ua_ts.login_hash IS NOT NULL AND v_ua_ts.login_hash != v_login_ts.login_hash THEN
              RAISE EXCEPTION
                  'Refusing to re-couple user (login=%), which had a unix account in the past, '
                  'to a new unix-account (uid=%). '
                  'Manually update the tombstones if you know what you are doing.',
                  NEW.login, v_ua.uid
                  USING ERRCODE = 'check_violation';
          END IF;
          update unix_tombstone ts set login_hash = v_u_login_hash where ts.uid = v_ua.uid;
      END IF;
      RETURN NEW;
  END IF;

  ------------
  -- UPDATE --
  ------------

  IF NEW.unix_account_id = OLD.unix_account_id THEN
      -- NOTE: this also means we _do nothing_ on a `login` update.
      -- This is a conscious decision, because we want the SQL operator
      -- to handle tombstones explicitly in this scenario.
      RETURN NEW;
  END IF;

  IF v_ua IS NULL THEN
      -- this is an UPDATE user SET unix_account_id=null. Nothing to do.
      RETURN NEW;
  END IF;

  -----------------------
  -- User → UA exists; --
  -----------------------
  select * into v_ua_ts from unix_tombstone ts where ts.uid = v_ua.uid;

  IF NOT v_ua_ts.login_hash IS NULL AND v_ua_ts.login_hash <> v_u_login_hash THEN
      RAISE EXCEPTION
          'Refusing to re-couple unix-account (uid=%), which belonged to a user in the past, to another user (login=%).'
          'Manually update the tombstones if you know what you are doing.',
          v_ua.uid, NEW.login
          USING ERRCODE = 'check_violation';
  END IF;

  ASSERT NOT v_login_ts IS NULL, 'existing user % does not have a tombstone', NEW.login;
  IF v_login_ts.uid IS NULL THEN
      -- gonna update ua's tombstone, so let's throw away user's tombstone
      set constraints user_login_hash_fkey deferred;
      delete from unix_tombstone where login_hash = v_u_login_hash;
      update unix_tombstone ts set login_hash = v_u_login_hash where ts.uid = v_ua_ts.uid;
      set constraints user_login_hash_fkey immediate;
  ELSE
      -- this smells wrong: either they already share a tombstone,
      -- or the user already _had_ a unix account!
      IF NOT v_ua_ts.login_hash IS NULL AND v_ua_ts.login_hash != v_login_ts.login_hash THEN
          RAISE EXCEPTION
              'Refusing to re-couple user (login=%), which had a unix account in the past, '
              'to a new unix-account (uid=%). '
              'Manually update the tombstones if you know what you are doing.',
              NEW.login, v_ua.uid
              USING ERRCODE = 'check_violation';
      END IF;
  END IF;

  update unix_tombstone ts set login_hash = v_u_login_hash where ts.uid = v_ua_ts.uid;
  RETURN NEW;
END;
$$;
CREATE TRIGGER user_ensure_tombstone_trigger BEFORE INSERT OR UPDATE OF unix_account_id, login ON "user" FOR EACH ROW EXECUTE PROCEDURE user_ensure_tombstone();
CREATE OR REPLACE FUNCTION check_tombstone_consistency() RETURNS trigger VOLATILE STRICT LANGUAGE plpgsql AS $$
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
            'trigger can only be invoked on user or unix_account tables, not %',
            TG_TABLE_NAME
        USING ERRCODE = 'feature_not_supported';
    END IF;

    IF v_ua IS NULL OR v_user IS NULL THEN
        RETURN NEW; -- no consistency to satisfy
    END IF;
    ASSERT NOT v_user IS NULL, 'v_user is null!';
    ASSERT NOT v_user.login IS NULL, format('user.login is null (%s): %s (type %s)', v_user.login, v_user, pg_typeof(v_user));

    select * into v_user_ts from unix_tombstone ts where ts.login_hash = v_user.login_hash;
    select * into v_ua_ts from unix_tombstone ts where ts.uid = v_ua.uid;

    -- this should already be ensured by the `ensure_*_tombstone` triggers,
    -- but we are defensive here to ensure consistency no matter what
    IF v_ua_ts IS NULL THEN
        ASSERT NOT v_ua IS NULL, 'unix_account is null';
        RAISE EXCEPTION
            'unix account with id=% (uid=%) has no tombstone.', v_ua.id, v_ua.uid
        USING ERRCODE = 'foreign_key_violation';
    END IF;
    IF v_user_ts IS NULL THEN
        RAISE EXCEPTION
            'user % with id=% (login=%) has no tombstone.', v_user, v_user.id, v_user.login
        USING ERRCODE = 'foreign_key_violation';
    END IF;

    if v_user_ts <> v_ua_ts THEN
        RAISE EXCEPTION
            'User tombstone (uid=%, login_hash=%) and unix account tombstone (uid=%, login_hash=%) differ!',
            v_user_ts.uid, v_user_ts.login_hash, v_ua_ts.uid, v_ua_ts.login_hash
        USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;
CREATE CONSTRAINT TRIGGER user_check_tombstone_consistency_trigger AFTER INSERT OR UPDATE OF unix_account_id, login ON "user" DEFERRABLE FOR EACH ROW EXECUTE PROCEDURE check_tombstone_consistency();
CREATE CONSTRAINT TRIGGER unix_account_check_tombstone_consistency_trigger AFTER INSERT OR UPDATE OF uid ON unix_account DEFERRABLE FOR EACH ROW EXECUTE PROCEDURE check_tombstone_consistency()
"""

# > from pycroft.model import unix_account as ua
# > from tests.model.ddl import literal_compile
# > print("\n".join(literal_compile(d).replace("%%", "%") for _, c, d in ua.manager.objects))
SQL_TRIGGERS_DROP = """
DROP FUNCTION IF EXISTS check_unix_tombstone_lifecycle();
DROP TRIGGER IF EXISTS check_unix_tombstone_lifecycle_trigger ON unix_tombstone;
DROP TRIGGER IF EXISTS unix_account_ensure_tombstone_trigger ON unix_account;
DROP FUNCTION IF EXISTS unix_account_ensure_tombstone();
DROP TRIGGER IF EXISTS user_ensure_tombstone_trigger ON "user";
DROP FUNCTION IF EXISTS user_ensure_tombstone();
DROP TRIGGER IF EXISTS user_check_tombstone_consistency_trigger ON "user";
DROP TRIGGER IF EXISTS unix_account_check_tombstone_consistency_trigger ON unix_account;
DROP FUNCTION IF EXISTS check_tombstone_consistency();
"""
