"""fix finance triggers

Revision ID: 7855ecffe722
Revises: 9a291ca0e06e
Create Date: 2019-03-05 23:22:32.642764

"""
from alembic import op
import sqlalchemy as sa
import pycroft


# revision identifiers, used by Alembic.
revision = '7855ecffe722'
down_revision = '9a291ca0e06e'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE OR REPLACE FUNCTION public.split_check_transaction_balanced()
         RETURNS trigger
         LANGUAGE plpgsql
         STABLE STRICT
        AS $function$
        DECLARE
          s split;
          count integer;
          balance integer;
          transaction_deleted boolean;
        BEGIN
          IF TG_OP = 'DELETE' THEN
            s := OLD;
          ELSE
            s := COALESCE(NEW, OLD);
          END IF;
          
          SELECT COUNT(*) = 0 INTO transaction_deleted FROM "transaction" WHERE "id" = s.transaction_id;
            
          SELECT COUNT(*), SUM(amount) INTO STRICT count, balance FROM split
              WHERE transaction_id = s.transaction_id;
          IF count < 2 AND NOT transaction_deleted THEN
            RAISE EXCEPTION 'transaction % has less than two splits %',
            s.transaction_id,
            transaction_deleted
            USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          IF balance <> 0 THEN
            RAISE EXCEPTION 'transaction % not balanced',
                s.transaction_id
                USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          RETURN NULL;
        END;$function$
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.bank_account_activity_matches_referenced_split()
         RETURNS trigger
         LANGUAGE plpgsql
         STABLE STRICT
        AS $function$DECLARE
          v_activity bank_account_activity;
          v_bank_account_account_id integer;
          v_split split;
        BEGIN
          IF TG_OP = 'DELETE' THEN
            v_activity := OLD;
          ELSE
            v_activity := COALESCE(NEW, OLD);
          END IF;
          SELECT bank_account.account_id INTO v_bank_account_account_id FROM bank_account
              WHERE bank_account.id = v_activity.bank_account_id;
          SELECT * INTO v_split FROM split
              WHERE split.transaction_id = v_activity.transaction_id
              AND split.account_id = v_activity.account_id;
          IF v_bank_account_account_id <> v_activity.account_id THEN
            RAISE EXCEPTION 'bank_account_activity %: account_id of referenced bank_account %  is different (% <> %)',
                v_activity.id, v_activity.bank_account_id, v_activity.account_id, v_bank_account_account_id
                USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          IF v_split IS NOT NULL AND v_split.amount <> v_activity.amount THEN
            RAISE EXCEPTION 'bank_account_activity %: amount of referenced split % is different (% <> %)',
                v_activity.id, v_split.id, v_activity.amount, v_split.amount
                USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          RETURN NULL;
        END;
        $function$
    """)


def downgrade():
    pass
