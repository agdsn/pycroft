"""Remove traffic credit and groups

Revision ID: 9a291ca0e06e
Revises: 7a6449f2489c
Create Date: 2019-01-25 15:38:52.300698

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9a291ca0e06e'
down_revision = '7a6449f2489c'
branch_labels = None
depends_on = None


def upgrade():
    group = sa.table('group', sa.column('type', sa.String))

    op.drop_index('ix_traffic_credit_user_id', table_name='traffic_credit')

    op.execute("DROP VIEW IF EXISTS current_traffic_balance")

    op.drop_index('ix_building_default_traffic_group_id', table_name='building')
    op.drop_constraint('building_default_traffic_group_id_fkey', 'building',
                       type_='foreignkey')
    op.drop_column('building', 'default_traffic_group_id')

    op.drop_table('traffic_credit')
    op.drop_table('traffic_group')
    op.drop_table('traffic_balance')

    op.execute(group.delete().where(group.c.type == 'traffic_group'))

    op.execute("DROP FUNCTION IF EXISTS traffic_history (arg_user_id int, arg_start timestamptz, arg_interval interval, arg_step interval)")

    op.execute('''
        CREATE OR REPLACE FUNCTION traffic_history (arg_user_id int, arg_start timestamptz, arg_end timestamptz)  RETURNS TABLE ("timestamp" timestamptz, ingress numeric, egress numeric) STABLE LANGUAGE sql AS $$
        WITH anon_3 AS 
        (SELECT sum(traffic_volume.amount) AS amount, day, CAST(traffic_volume.type AS TEXT) AS type 
        FROM generate_series(date_trunc('day', arg_start), date_trunc('day', arg_end), '1 day') AS day 
        LEFT OUTER JOIN traffic_volume ON date_trunc('day', traffic_volume.timestamp) = day AND traffic_volume.user_id = arg_user_id
        GROUP BY day, type), 
        anon_1 AS 
        (SELECT anon_3.amount AS amount, anon_3.day, anon_3.type AS type 
        FROM anon_3 
        WHERE anon_3.type = 'Ingress' OR anon_3.type IS NULL), 
        anon_2 AS 
        (SELECT anon_3.amount AS amount, anon_3.day, anon_3.type AS type 
        FROM anon_3 
        WHERE anon_3.type = 'Egress' OR anon_3.type IS NULL)
         SELECT coalesce(anon_1.day, anon_2.day) AS timestamp, anon_1.amount AS ingress, anon_2.amount AS egress 
        FROM anon_1 FULL OUTER JOIN anon_2 ON anon_1.day = anon_2.day ORDER BY timestamp
        $$
    ''')


def downgrade():
    op.create_table('traffic_group',
                    sa.Column('id', sa.INTEGER(), autoincrement=False,
                              nullable=False),
                    sa.Column('credit_limit', sa.BIGINT(), autoincrement=False,
                              nullable=False),
                    sa.Column('credit_interval', postgresql.INTERVAL(),
                              autoincrement=False, nullable=False),
                    sa.Column('credit_amount', sa.BIGINT(), autoincrement=False,
                              nullable=False),
                    sa.Column('initial_credit_amount', sa.BIGINT(),
                              autoincrement=False, nullable=False),
                    sa.ForeignKeyConstraint(['id'], ['group.id'],
                                            name='traffic_group_id_fkey'),
                    sa.PrimaryKeyConstraint('id', name='traffic_group_pkey'),
                    postgresql_ignore_search_path=False
                    )

    op.add_column('building',
                  sa.Column('default_traffic_group_id', sa.INTEGER(),
                            autoincrement=False, nullable=True))
    op.create_foreign_key('building_default_traffic_group_id_fkey', 'building',
                          'traffic_group', ['default_traffic_group_id'], ['id'])
    op.create_index('ix_building_default_traffic_group_id', 'building',
                    ['default_traffic_group_id'], unique=False)
    op.create_table('traffic_balance',
                    sa.Column('user_id', sa.INTEGER(), autoincrement=False,
                              nullable=False),
                    sa.Column('amount', sa.BIGINT(), autoincrement=False,
                              nullable=False),
                    sa.Column('timestamp', postgresql.TIMESTAMP(timezone=True),
                              server_default=sa.text('CURRENT_TIMESTAMP'),
                              autoincrement=False, nullable=False),
                    sa.ForeignKeyConstraint(['user_id'], ['user.id'],
                                            name='traffic_balance_user_id_fkey',
                                            ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('user_id',
                                            name='traffic_balance_pkey')
                    )

    op.create_table('traffic_credit',
                    sa.Column('id', sa.INTEGER(), autoincrement=True,
                              nullable=False),
                    sa.Column('timestamp', postgresql.TIMESTAMP(timezone=True),
                              server_default=sa.text('CURRENT_TIMESTAMP'),
                              autoincrement=False, nullable=False),
                    sa.Column('amount', sa.BIGINT(), autoincrement=False,
                              nullable=False),
                    sa.Column('user_id', sa.INTEGER(), autoincrement=False,
                              nullable=False),
                    sa.CheckConstraint('amount >= 0',
                                       name='traffic_credit_amount_check'),
                    sa.ForeignKeyConstraint(['user_id'], ['user.id'],
                                            name='traffic_credit_user_id_fkey',
                                            ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id', name='traffic_credit_pkey')
                    )
    op.create_index('ix_traffic_credit_user_id', 'traffic_credit', ['user_id'],
                    unique=False)

    op.execute('''
        CREATE OR REPLACE VIEW current_traffic_balance AS
 SELECT "user".id AS user_id,
    (((COALESCE(traffic_balance.amount, (0)::bigint))::numeric + COALESCE(recent_credit.amount, (0)::numeric)) - COALESCE(recent_volume.amount, (0)::numeric)) AS amount
   FROM ((("user"
     LEFT JOIN traffic_balance ON (("user".id = traffic_balance.user_id)))
     LEFT JOIN LATERAL ( SELECT sum(traffic_credit.amount) AS amount
           FROM traffic_credit
          WHERE (("user".id = traffic_credit.user_id) AND ((traffic_balance.user_id IS NULL) OR (traffic_balance."timestamp" <= traffic_credit."timestamp")))) recent_credit ON (true))
     LEFT JOIN LATERAL ( SELECT sum(traffic_volume.amount) AS amount
           FROM traffic_volume
          WHERE (("user".id = traffic_volume.user_id) AND ((traffic_balance.user_id IS NULL) OR (traffic_balance."timestamp" <= traffic_volume."timestamp")))) recent_volume ON (true));
    ''')

    op.execute("DROP FUNCTION IF EXISTS traffic_history (arg_user_id int, arg_start timestamptz, arg_end timestamptz)")

    op.execute('''
        CREATE OR REPLACE FUNCTION traffic_history (arg_user_id int, arg_start timestamptz, arg_interval interval, arg_step interval) RETURNS TABLE ("timestamp" timestamptz, credit numeric, ingress numeric, egress numeric, balance numeric) STABLE LANGUAGE sql AS $$
        WITH balance AS 
        (SELECT traffic_balance.amount AS amount, traffic_balance.timestamp AS timestamp 
        FROM "user" LEFT OUTER JOIN traffic_balance ON "user".id = traffic_balance.user_id 
        WHERE "user".id = arg_user_id), 
        traffic_events AS 
        (SELECT traffic_credit.amount AS amount, traffic_credit.timestamp AS timestamp, 'Credit' AS type 
        FROM traffic_credit 
        WHERE traffic_credit.user_id = arg_user_id UNION ALL SELECT -traffic_volume.amount AS amount, traffic_volume.timestamp AS timestamp, CAST(traffic_volume.type AS TEXT) AS type 
        FROM traffic_volume 
        WHERE traffic_volume.user_id = arg_user_id), 
        buckets AS 
        (SELECT bucket, row_number() OVER (ORDER BY bucket) - 1 AS index 
        FROM generate_series(CAST(to_timestamp(trunc(EXTRACT(epoch FROM CAST(arg_start AS TIMESTAMP WITH TIME ZONE)) / EXTRACT(epoch FROM arg_step)) * EXTRACT(epoch FROM arg_step)) AS TIMESTAMP WITH TIME ZONE) - arg_step, CAST(to_timestamp(trunc(EXTRACT(epoch FROM CAST(arg_start AS TIMESTAMP WITH TIME ZONE) + arg_interval) / EXTRACT(epoch FROM arg_step)) * EXTRACT(epoch FROM arg_step)) AS TIMESTAMP WITH TIME ZONE), arg_step) AS bucket ORDER BY bucket), 
        traffic_hist AS 
        (SELECT buckets.bucket, sum(CASE WHEN (traffic_events.type = 'Credit') THEN traffic_events.amount END) AS credit, sum(CASE WHEN (traffic_events.type = 'Ingress') THEN -traffic_events.amount END) AS ingress, sum(CASE WHEN (traffic_events.type = 'Egress') THEN -traffic_events.amount END) AS egress, sum(traffic_events.amount) AS amount, sum(CASE WHEN ((SELECT balance.timestamp 
        FROM balance) IS NOT NULL AND traffic_events.timestamp < (SELECT balance.timestamp 
        FROM balance)) THEN traffic_events.amount END) AS before_balance, sum(CASE WHEN ((SELECT balance.timestamp 
        FROM balance) IS NULL OR traffic_events.timestamp >= (SELECT balance.timestamp 
        FROM balance)) THEN traffic_events.amount END) AS after_balance 
        FROM buckets LEFT OUTER JOIN traffic_events ON width_bucket(traffic_events.timestamp, (SELECT array((SELECT buckets.bucket 
        FROM buckets 
        WHERE buckets.index != 0)) AS array_1)) = buckets.index 
        WHERE buckets.index < (SELECT max(buckets.index) AS max_1 
        FROM buckets) GROUP BY buckets.bucket ORDER BY buckets.bucket)
         SELECT agg_hist.bucket, agg_hist.credit, agg_hist.ingress, agg_hist.egress, agg_hist.balance 
        FROM (SELECT traffic_hist.bucket, traffic_hist.credit AS credit, traffic_hist.ingress AS ingress, traffic_hist.egress AS egress, CASE WHEN ((SELECT balance.timestamp 
        FROM balance) IS NOT NULL AND traffic_hist.bucket < (SELECT balance.timestamp 
        FROM balance) AND ((SELECT min(traffic_events.timestamp) AS min_1 
        FROM traffic_events) IS NULL OR traffic_hist.bucket < (SELECT min(traffic_events.timestamp) AS min_1 
        FROM traffic_events))) THEN NULL WHEN ((SELECT balance.timestamp 
        FROM balance) IS NULL OR traffic_hist.bucket >= (SELECT balance.timestamp 
        FROM balance)) THEN coalesce((SELECT balance.amount 
        FROM balance), 0) + coalesce(sum(traffic_hist.after_balance) OVER (ORDER BY traffic_hist.bucket ASC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 0) ELSE (coalesce((SELECT balance.amount 
        FROM balance), 0) + coalesce(traffic_hist.after_balance, 0)) - coalesce(sum(traffic_hist.before_balance) OVER (ORDER BY traffic_hist.bucket DESC ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) END AS balance 
        FROM traffic_hist) AS agg_hist ORDER BY agg_hist.bucket 
         LIMIT ALL OFFSET 1
        $$
    ''')
