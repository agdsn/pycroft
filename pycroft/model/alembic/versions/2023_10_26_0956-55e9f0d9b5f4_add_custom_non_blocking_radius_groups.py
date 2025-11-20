"""Add custom non-blocking radius groups

Revision ID: 55e9f0d9b5f4
Revises: 249743eb7b94
Create Date: 2023-10-26 08:34:11.939772

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "55e9f0d9b5f4"
down_revision = "249743eb7b94"
branch_labels = None
depends_on = None


def upgrade():
    # unfortunately, `op.add_column` does not support `if not exists`
    op.execute(
        "ALTER TABLE radius_property ADD COLUMN IF NOT EXISTS hades_group_name varchar"
    )
    op.add_column("radius_property", sa.Column("is_blocking_group", sa.Boolean()))

    ## DATA MIGRATION
    NAME_MAPPING = (
        ("payment_in_default", "default_in_payment"),
        ("traffic_limit_exceeded", "traffic"),
        ("ZW41_acltestproperty", "ZW41_untagged_acltest"),
        ("Wu3_acltestproperty", "Wu3_untagged_acltest"),
    )
    for p, hgn in NAME_MAPPING:
        op.execute(
            f"update radius_property set hades_group_name='{hgn}' where property='{p}'"
        )
    op.execute(
        "update radius_property set hades_group_name=property where hades_group_name is null"
    )

    BLOCKING_PROPS = ("violation", "payment_in_default", "traffic_limit_exceeded")
    blocking_props_list = ", ".join(f"'{p}'" for p in BLOCKING_PROPS)
    op.execute(
        f"update radius_property set is_blocking_group=(property in ({blocking_props_list}));"
    )

    op.alter_column("radius_property", "hades_group_name", nullable=False)
    op.alter_column("radius_property", "is_blocking_group", nullable=False)
    ## /DATA MIGRATION

    op.execute(
        """
        CREATE OR REPLACE VIEW radusergroup AS
        SELECT interface.mac::text AS "UserName",
            host(switch.management_ip) AS "NASIPAddress",
            switch_port.name AS "NASPortId",
            vlan.name::text || '_untagged'::text AS "GroupName",
            20 AS "Priority"
           FROM "user"
             JOIN host ON "user".id = host.owner_id
             JOIN interface ON host.id = interface.host_id
             JOIN room ON room.id = host.room_id
             JOIN patch_port ON patch_port.room_id = room.id AND patch_port.switch_port_id IS NOT NULL
             JOIN switch_port ON switch_port.id = patch_port.switch_port_id
             JOIN switch ON switch.host_id = switch_port.switch_id
             JOIN ip ON interface.id = ip.interface_id
             JOIN subnet ON subnet.id = ip.subnet_id
             JOIN vlan ON vlan.id = subnet.vlan_id
             JOIN current_property ON "user".id = current_property.user_id AND NOT current_property.denied
          WHERE current_property.property_name::text = 'network_access'::text
        UNION ALL
         SELECT interface.mac::text AS "UserName",
            host(switch.management_ip) AS "NASIPAddress",
            switch_port.name AS "NASPortId",
            radius_property.hades_group_name AS "GroupName",
                CASE
                    WHEN radius_property.is_blocking_group THEN '-10'::integer
                    ELSE 10
                END AS "Priority"
           FROM "user"
             JOIN host ON "user".id = host.owner_id
             JOIN interface ON host.id = interface.host_id
             JOIN room ON room.id = host.room_id
             JOIN patch_port ON patch_port.room_id = room.id AND patch_port.switch_port_id IS NOT NULL
             JOIN switch_port ON switch_port.id = patch_port.switch_port_id
             JOIN switch ON switch.host_id = switch_port.switch_id
             JOIN current_property ON "user".id = current_property.user_id AND NOT current_property.denied
             JOIN radius_property ON radius_property.property::text = current_property.property_name::text
        UNION ALL
         SELECT interface.mac::text AS "UserName",
            host(switch.management_ip) AS "NASIPAddress",
            switch_port.name AS "NASPortId",
            'no_network_access'::text AS "GroupName",
            0 AS "Priority"
           FROM "user"
             LEFT JOIN ( SELECT current_property.user_id,
                    1 AS network_access
                   FROM current_property
                  WHERE current_property.property_name::text = 'network_access'::text AND NOT current_property.denied) users_with_network_access 
               ON "user".id = users_with_network_access.user_id
             JOIN host ON "user".id = host.owner_id
             JOIN interface ON host.id = interface.host_id
             JOIN room ON room.id = host.room_id
             JOIN patch_port ON patch_port.room_id = room.id AND patch_port.switch_port_id IS NOT NULL
             JOIN switch_port ON switch_port.id = patch_port.switch_port_id
             JOIN switch ON switch.host_id = switch_port.switch_id
          WHERE users_with_network_access.network_access IS NULL
        UNION ALL
         SELECT 'unknown'::text AS "UserName",
            NULL::text AS "NASIPAddress",
            NULL::character varying AS "NASPortId",
            'unknown'::text AS "GroupName",
            1 AS "Priority";
    """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW radgroupreply AS
        SELECT radgroupreply_base."GroupName",
            radgroupreply_base."Attribute",
            radgroupreply_base."Op",
            radgroupreply_base."Value"
           FROM radgroupreply_base
        UNION ALL
         SELECT vlan.name::text || '_untagged'::text AS "GroupName",
            'Egress-VLAN-Name'::character varying AS "Attribute",
            '+='::character varying AS "Op",
            '2'::text || vlan.name::text AS "Value"
           FROM vlan
        UNION ALL
         SELECT vlan.name::text || '_tagged'::text AS "GroupName",
            'Egress-VLAN-Name'::character varying AS "Attribute",
            '+='::character varying AS "Op",
            '1'::text || vlan.name::text AS "Value"
           FROM vlan
        UNION ALL
         SELECT vlan.name::text || '_untagged'::text AS "GroupName",
            'Fall-Through'::character varying AS "Attribute",
            ':='::character varying AS "Op",
            'Yes'::character varying AS "Value"
           FROM vlan
        UNION ALL
         SELECT vlan.name::text || '_tagged'::text AS "GroupName",
            'Fall-Through'::character varying AS "Attribute",
            ':='::character varying AS "Op",
            'Yes'::character varying AS "Value"
           FROM vlan
        UNION ALL
         SELECT radius_property.hades_group_name AS "GroupName",
            'Egress-VLAN-Name'::character varying AS "Attribute",
            ':='::character varying AS "Op",
            '2hades-unauth'::character varying AS "Value"
           FROM radius_property
          WHERE radius_property.is_blocking_group
        UNION ALL
         SELECT radius_property.hades_group_name AS "GroupName",
            'Fall-Through'::character varying AS "Attribute",
            ':='::character varying AS "Op",
            'No'::character varying AS "Value"
           FROM radius_property
          WHERE radius_property.is_blocking_group
        UNION ALL
         SELECT 'no_network_access'::character varying AS "GroupName",
            'Egress-VLAN-Name'::character varying AS "Attribute",
            ':='::character varying AS "Op",
            '2hades-unauth'::character varying AS "Value"
        UNION ALL
         SELECT 'no_network_access'::character varying AS "GroupName",
            'Fall-Through'::character varying AS "Attribute",
            ':='::character varying AS "Op",
            'No'::character varying AS "Value";                  
    """
    )


def downgrade():
    op.execute(
        """
        CREATE OR REPLACE VIEW radgroupreply AS
        SELECT radgroupreply_base."GroupName",
            radgroupreply_base."Attribute",
            radgroupreply_base."Op",
            radgroupreply_base."Value"
           FROM radgroupreply_base
        UNION ALL
         SELECT vlan.name::text || '_untagged'::text AS "GroupName",
            'Egress-VLAN-Name'::character varying AS "Attribute",
            '+='::character varying AS "Op",
            '2'::text || vlan.name::text AS "Value"
           FROM vlan
        UNION ALL
         SELECT vlan.name::text || '_tagged'::text AS "GroupName",
            'Egress-VLAN-Name'::character varying AS "Attribute",
            '+='::character varying AS "Op",
            '1'::text || vlan.name::text AS "Value"
           FROM vlan
        UNION ALL
         SELECT vlan.name::text || '_untagged'::text AS "GroupName",
            'Fall-Through'::character varying AS "Attribute",
            ':='::character varying AS "Op",
            'Yes'::character varying AS "Value"
           FROM vlan
        UNION ALL
         SELECT vlan.name::text || '_tagged'::text AS "GroupName",
            'Fall-Through'::character varying AS "Attribute",
            ':='::character varying AS "Op",
            'Yes'::character varying AS "Value"
           FROM vlan
        UNION ALL
         SELECT radius_property.property AS "GroupName",
            'Egress-VLAN-Name'::character varying AS "Attribute",
            ':='::character varying AS "Op",
            '2hades-unauth'::character varying AS "Value"
           FROM radius_property
        UNION ALL
         SELECT radius_property.property AS "GroupName",
            'Fall-Through'::character varying AS "Attribute",
            ':='::character varying AS "Op",
            'No'::character varying AS "Value"
           FROM radius_property
        UNION ALL
         SELECT 'no_network_access'::character varying AS "GroupName",
            'Egress-VLAN-Name'::character varying AS "Attribute",
            ':='::character varying AS "Op",
            '2hades-unauth'::character varying AS "Value"
        UNION ALL
         SELECT 'no_network_access'::character varying AS "GroupName",
            'Fall-Through'::character varying AS "Attribute",
            ':='::character varying AS "Op",
            'No'::character varying AS "Value";
    """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW radusergroup AS
         SELECT interface.mac::text AS "UserName",
            host(switch.management_ip) AS "NASIPAddress",
            switch_port.name AS "NASPortId",
            vlan.name::text || '_untagged'::text AS "GroupName",
            20 AS "Priority"
           FROM "user"
             JOIN host ON "user".id = host.owner_id
             JOIN interface ON host.id = interface.host_id
             JOIN room ON room.id = host.room_id
             JOIN patch_port ON patch_port.room_id = room.id AND patch_port.switch_port_id IS NOT NULL
             JOIN switch_port ON switch_port.id = patch_port.switch_port_id
             JOIN switch ON switch.host_id = switch_port.switch_id
             JOIN ip ON interface.id = ip.interface_id
             JOIN subnet ON subnet.id = ip.subnet_id
             JOIN vlan ON vlan.id = subnet.vlan_id
             JOIN current_property ON "user".id = current_property.user_id AND NOT current_property.denied
          WHERE current_property.property_name::text = 'network_access'::text
        UNION ALL
         SELECT interface.mac::text AS "UserName",
            host(switch.management_ip) AS "NASIPAddress",
            switch_port.name AS "NASPortId",
            radius_property.property AS "GroupName",
            '-10'::integer AS "Priority"
           FROM "user"
             JOIN host ON "user".id = host.owner_id
             JOIN interface ON host.id = interface.host_id
             JOIN room ON room.id = host.room_id
             JOIN patch_port ON patch_port.room_id = room.id AND patch_port.switch_port_id IS NOT NULL
             JOIN switch_port ON switch_port.id = patch_port.switch_port_id
             JOIN switch ON switch.host_id = switch_port.switch_id
             JOIN current_property ON "user".id = current_property.user_id AND NOT current_property.denied
             JOIN radius_property ON radius_property.property::text = current_property.property_name::text
        UNION ALL
         SELECT interface.mac::text AS "UserName",
            host(switch.management_ip) AS "NASIPAddress",
            switch_port.name AS "NASPortId",
            'no_network_access'::text AS "GroupName",
            0 AS "Priority"
           FROM "user"
             LEFT JOIN ( SELECT current_property.user_id,
                    1 AS network_access
                   FROM current_property
                  WHERE current_property.property_name::text = 'network_access'::text AND NOT current_property.denied) users_with_network_access 
               ON "user".id = users_with_network_access.user_id
             JOIN host ON "user".id = host.owner_id
             JOIN interface ON host.id = interface.host_id
             JOIN room ON room.id = host.room_id
             JOIN patch_port ON patch_port.room_id = room.id AND patch_port.switch_port_id IS NOT NULL
             JOIN switch_port ON switch_port.id = patch_port.switch_port_id
             JOIN switch ON switch.host_id = switch_port.switch_id
          WHERE users_with_network_access.network_access IS NULL
        UNION ALL
         SELECT 'unknown'::text AS "UserName",
            NULL::text AS "NASIPAddress",
            NULL::character varying AS "NASPortId",
            'unknown'::text AS "GroupName",
            1 AS "Priority";
    """
    )

    op.drop_column("radius_property", "is_blocking_group")
    op.drop_column("radius_property", "hades_group_name")
