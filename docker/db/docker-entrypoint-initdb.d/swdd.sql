CREATE SCHEMA IF NOT EXISTS "swdd";

create table if not exists swdd.swdd_vo (
    "vo_id" int,
    "suchname" text,
    "name" text,
    "voart_id" int,
    "nutzungsart_id" int,
    "nutzbarvon" date,
    "nutzbarbis" date,
    "status" int,
    "wohnheim_id" int,
    "wohnheim_suchname" text,
    "wohnheim_name" text,
    "stockwerk_id" int,
    "stockwerk" text,
    "stockwerk_name" text,
    "haus_id" int,
    "haus_name" text
);

create table if not exists swdd.swdd_vv (
    "persvv_id" int,
    "person_id" int,
    "vo_suchname" text,
    "person_hash" text,
    "mietbeginn" date,
    "mietende" date,
    "status_id" int
);

create table if not exists swdd.swdd_import (
    "id" int,
    "date" timestamp,
    "type" text
);

/* Test 1 1990-01-01 */
insert into swdd.swdd_vv
    (persvv_id, person_id, vo_suchname, person_hash, mietbeginn, mietende, status_id)
    VALUES (1, 1, '1', 'F36B1F2C12FDA189821A72B6E16626FAAF73FF36C1E36E273848F1980B5D1EE9858330F528661AE724F5F52070A54802623AD50AE0A29E12ED184E4CD3DCF9C3',
            '2020-01-01', '2023-09-30', 2);

/* Test 2 2005-01-01 */
insert into swdd.swdd_vv
    (persvv_id, person_id, vo_suchname, person_hash, mietbeginn, mietende, status_id)
    VALUES (2, 2, '2', 'EC350C5A3DCFF89B758366A406DEC390D0BD986C9B15D25F1F5063EBFB4B22D18B16D908B89E9F7E21506544533A2DBCFCABCDA2BA927BCB95B96FAE799D9598',
            '2020-01-01', '2023-09-30', 2);

/* Test 3 1990-01-01 */
insert into swdd.swdd_vv
    (persvv_id, person_id, vo_suchname, person_hash, mietbeginn, mietende, status_id)
    VALUES (3, 3, '3', '14CF79DDEDA9AE4FA4211C7D4D5A0B15E6F5531DCE7B822A5540D7977B311BAE10E9F8A4614AF417A9C32C3EAF0D13CB7F30868A76844C9D1E40AD0E320CB852',
            '2020-01-01', '2020-08-30', 2);

/* Test 4 1990-01-01 */
insert into swdd.swdd_vv
    (persvv_id, person_id, vo_suchname, person_hash, mietbeginn, mietende, status_id)
    VALUES (4, 4, '4', 'C65ED7EA8E116E9F14E4CB98BD5B04399C7477EF83822ADC5D5C0E20C1FA7DC31C1033ED6DE0A98CB9FF9FA9EA86C5B1ABFF4ED5C2C334227699C5133A544760',
            '2020-01-01', '2023-09-30', 1);

