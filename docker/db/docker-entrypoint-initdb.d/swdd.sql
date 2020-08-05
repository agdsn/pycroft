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
