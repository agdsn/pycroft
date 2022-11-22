"""add hostname column to dhcphost view

Revision ID: 249743eb7b94
Revises: 6815546f681c
Create Date: 2022-09-11 22:31:30.891486

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '249743eb7b94'
down_revision = '6815546f681c'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
		CREATE OR REPLACE VIEW dhcphost AS
		 SELECT interface.mac AS "Mac",
			host(ip.address) AS "IpAddress",
			host.name AS "Hostname"
		   FROM "user"
			 JOIN current_property ON "user".id = current_property.user_id AND NOT current_property.denied
			 JOIN host ON "user".id = host.owner_id
			 JOIN interface ON host.id = interface.host_id
			 JOIN ip ON interface.id = ip.interface_id
		  WHERE current_property.property_name::text = 'network_access'::text
    """)


def downgrade():
    op.execute("""
		CREATE OR REPLACE VIEW dhcphost AS
		 SELECT interface.mac AS "Mac",
			host(ip.address) AS "IpAddress"
		   FROM "user"
			 JOIN current_property ON "user".id = current_property.user_id AND NOT current_property.denied
			 JOIN host ON "user".id = host.owner_id
			 JOIN interface ON host.id = interface.host_id
			 JOIN ip ON interface.id = ip.interface_id
		  WHERE current_property.property_name::text = 'network_access'::text
    """)
