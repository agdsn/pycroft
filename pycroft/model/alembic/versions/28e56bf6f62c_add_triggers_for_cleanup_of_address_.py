"""Add triggers for cleanup of address orphans

Revision ID: 28e56bf6f62c
Revises: 5905825242ff
Create Date: 2021-02-12 02:07:00.403096

"""
from alembic import op
import sqlalchemy as sa
import pycroft


# revision identifiers, used by Alembic.
revision = '28e56bf6f62c'
down_revision = '5905825242ff'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE FUNCTION address_remove_orphans() RETURNS trigger VOLATILE STRICT LANGUAGE plpgsql AS $$
    BEGIN
      delete from address
      where not exists (select 1 from room where room.address_id = address.id)
      and not exists (select 1 from "user" where "user".address_id = address.id);
      RETURN NULL;
    END;
    $$""")
    op.execute("""
    CREATE TRIGGER user_address_cleanup_trigger AFTER UPDATE OR DELETE ON "user"
      FOR EACH ROW EXECUTE PROCEDURE address_remove_orphans()
    """)
    op.execute("""
    CREATE TRIGGER room_address_cleanup_trigger AFTER UPDATE OR DELETE ON room
      FOR EACH ROW EXECUTE PROCEDURE address_remove_orphans()
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS room_address_cleanup_trigger ON room")
    op.execute("DROP TRIGGER IF EXISTS user_address_cleanup_trigger ON \"user\"")
    op.execute("DROP FUNCTION IF EXISTS address_remove_orphans()")
