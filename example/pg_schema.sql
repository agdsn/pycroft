--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- Name: finance_account_type; Type: TYPE; Schema: public; Owner: vagrant
--

CREATE TYPE finance_account_type AS ENUM (
    'ASSET',
    'LIABILITY',
    'EXPENSE',
    'REVENUE'
);


ALTER TYPE public.finance_account_type OWNER TO vagrant;

--
-- Name: subnet_ip_type; Type: TYPE; Schema: public; Owner: vagrant
--

CREATE TYPE subnet_ip_type AS ENUM (
    '4',
    '6'
);


ALTER TYPE public.subnet_ip_type OWNER TO vagrant;

--
-- Name: traffic_types; Type: TYPE; Schema: public; Owner: vagrant
--

CREATE TYPE traffic_types AS ENUM (
    'IN',
    'OUT'
);


ALTER TYPE public.traffic_types OWNER TO vagrant;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: a_record; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE a_record (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    time_to_live integer,
    address_id integer NOT NULL
);


ALTER TABLE public.a_record OWNER TO vagrant;

--
-- Name: aaaa_record; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE aaaa_record (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    time_to_live integer,
    address_id integer NOT NULL
);


ALTER TABLE public.aaaa_record OWNER TO vagrant;

--
-- Name: association_dormitory_vlan; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE association_dormitory_vlan (
    dormitory_id integer,
    vlan_id integer
);


ALTER TABLE public.association_dormitory_vlan OWNER TO vagrant;

--
-- Name: association_subnet_vlan; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE association_subnet_vlan (
    subnet_id integer,
    vlan_id integer
);


ALTER TABLE public.association_subnet_vlan OWNER TO vagrant;

--
-- Name: cname_record; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE cname_record (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    record_for_id integer NOT NULL
);


ALTER TABLE public.cname_record OWNER TO vagrant;

--
-- Name: destination_port; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE destination_port (
    id integer NOT NULL
);


ALTER TABLE public.destination_port OWNER TO vagrant;

--
-- Name: dormitory; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE dormitory (
    id integer NOT NULL,
    number character varying(3) NOT NULL,
    short_name character varying(5) NOT NULL,
    street character varying(20) NOT NULL
);


ALTER TABLE public.dormitory OWNER TO vagrant;

--
-- Name: dormitory_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE dormitory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dormitory_id_seq OWNER TO vagrant;

--
-- Name: dormitory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE dormitory_id_seq OWNED BY dormitory.id;


--
-- Name: finance_account; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE finance_account (
    id integer NOT NULL,
    name character varying(127) NOT NULL,
    type finance_account_type NOT NULL
);


ALTER TABLE public.finance_account OWNER TO vagrant;

--
-- Name: finance_account_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE finance_account_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.finance_account_id_seq OWNER TO vagrant;

--
-- Name: finance_account_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE finance_account_id_seq OWNED BY finance_account.id;


--
-- Name: group; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE "group" (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    type character varying(17) NOT NULL
);


ALTER TABLE public."group" OWNER TO vagrant;

--
-- Name: group_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.group_id_seq OWNER TO vagrant;

--
-- Name: group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE group_id_seq OWNED BY "group".id;


--
-- Name: host; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE host (
    id integer NOT NULL,
    type character varying(50),
    user_id integer,
    room_id integer
);


ALTER TABLE public.host OWNER TO vagrant;

--
-- Name: host_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE host_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.host_id_seq OWNER TO vagrant;

--
-- Name: host_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE host_id_seq OWNED BY host.id;


--
-- Name: ip; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE ip (
    id integer NOT NULL,
    address character varying(51) NOT NULL,
    net_device_id integer NOT NULL,
    subnet_id integer NOT NULL
);


ALTER TABLE public.ip OWNER TO vagrant;

--
-- Name: ip_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE ip_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ip_id_seq OWNER TO vagrant;

--
-- Name: ip_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE ip_id_seq OWNED BY ip.id;


--
-- Name: journal; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE journal (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    bank character varying(255) NOT NULL,
    account_number character varying(10) NOT NULL,
    routing_number character varying(8) NOT NULL,
    iban character varying(34) NOT NULL,
    bic character varying(11) NOT NULL,
    hbci_url character varying(255) NOT NULL,
    finance_account_id integer NOT NULL
);


ALTER TABLE public.journal OWNER TO vagrant;

--
-- Name: journal_entry; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE journal_entry (
    id integer NOT NULL,
    journal_id integer NOT NULL,
    amount integer NOT NULL,
    description text NOT NULL,
    original_description text NOT NULL,
    other_account_number character varying(255) NOT NULL,
    other_routing_number character varying(255) NOT NULL,
    other_name character varying(255) NOT NULL,
    import_time timestamp without time zone NOT NULL,
    transaction_date date NOT NULL,
    valid_date date NOT NULL,
    transaction_id integer
);


ALTER TABLE public.journal_entry OWNER TO vagrant;

--
-- Name: journal_entry_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE journal_entry_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.journal_entry_id_seq OWNER TO vagrant;

--
-- Name: journal_entry_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE journal_entry_id_seq OWNED BY journal_entry.id;


--
-- Name: journal_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE journal_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.journal_id_seq OWNER TO vagrant;

--
-- Name: journal_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE journal_id_seq OWNED BY journal.id;


--
-- Name: log_entry; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE log_entry (
    id integer NOT NULL,
    type character varying(50),
    message text NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    author_id integer NOT NULL
);


ALTER TABLE public.log_entry OWNER TO vagrant;

--
-- Name: log_entry_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE log_entry_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.log_entry_id_seq OWNER TO vagrant;

--
-- Name: log_entry_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE log_entry_id_seq OWNED BY log_entry.id;


--
-- Name: membership; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE membership (
    id integer NOT NULL,
    start_date timestamp without time zone NOT NULL,
    end_date timestamp without time zone,
    group_id integer NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.membership OWNER TO vagrant;

--
-- Name: membership_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE membership_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.membership_id_seq OWNER TO vagrant;

--
-- Name: membership_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE membership_id_seq OWNED BY membership.id;


--
-- Name: mx_record; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE mx_record (
    id integer NOT NULL,
    server character varying(255) NOT NULL,
    domain character varying(255) NOT NULL,
    priority integer NOT NULL
);


ALTER TABLE public.mx_record OWNER TO vagrant;

--
-- Name: net_device; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE net_device (
    id integer NOT NULL,
    type character varying(50),
    mac character varying(17) NOT NULL,
    host_id integer NOT NULL
);


ALTER TABLE public.net_device OWNER TO vagrant;

--
-- Name: net_device_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE net_device_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.net_device_id_seq OWNER TO vagrant;

--
-- Name: net_device_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE net_device_id_seq OWNED BY net_device.id;


--
-- Name: ns_record; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE ns_record (
    id integer NOT NULL,
    domain character varying(255) NOT NULL,
    server character varying(255) NOT NULL,
    time_to_live integer
);


ALTER TABLE public.ns_record OWNER TO vagrant;

--
-- Name: patch_port; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE patch_port (
    id integer NOT NULL,
    destination_port_id integer,
    room_id integer NOT NULL
);


ALTER TABLE public.patch_port OWNER TO vagrant;

--
-- Name: phone_port; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE phone_port (
    id integer NOT NULL
);


ALTER TABLE public.phone_port OWNER TO vagrant;

--
-- Name: port; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE port (
    id integer NOT NULL,
    type character varying(15) NOT NULL,
    name character varying(8) NOT NULL
);


ALTER TABLE public.port OWNER TO vagrant;

--
-- Name: port_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE port_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.port_id_seq OWNER TO vagrant;

--
-- Name: port_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE port_id_seq OWNED BY port.id;


--
-- Name: property; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE property (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    granted boolean NOT NULL,
    property_group_id integer NOT NULL
);


ALTER TABLE public.property OWNER TO vagrant;

--
-- Name: property_group; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE property_group (
    id integer NOT NULL
);


ALTER TABLE public.property_group OWNER TO vagrant;

--
-- Name: property_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE property_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.property_id_seq OWNER TO vagrant;

--
-- Name: property_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE property_id_seq OWNED BY property.id;


--
-- Name: record; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE record (
    id integer NOT NULL,
    type character varying(50),
    host_id integer NOT NULL
);


ALTER TABLE public.record OWNER TO vagrant;

--
-- Name: record_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE record_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.record_id_seq OWNER TO vagrant;

--
-- Name: record_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE record_id_seq OWNED BY record.id;


--
-- Name: room; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE room (
    id integer NOT NULL,
    number character varying(36) NOT NULL,
    level integer NOT NULL,
    inhabitable boolean NOT NULL,
    dormitory_id integer NOT NULL
);


ALTER TABLE public.room OWNER TO vagrant;

--
-- Name: room_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE room_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.room_id_seq OWNER TO vagrant;

--
-- Name: room_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE room_id_seq OWNED BY room.id;


--
-- Name: room_log_entry; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE room_log_entry (
    id integer NOT NULL,
    room_id integer NOT NULL
);


ALTER TABLE public.room_log_entry OWNER TO vagrant;

--
-- Name: semester; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE semester (
    id integer NOT NULL,
    name character varying NOT NULL,
    registration_fee integer NOT NULL,
    regular_semester_contribution integer NOT NULL,
    reduced_semester_contribution integer NOT NULL,
    overdue_fine integer NOT NULL,
    premature_begin_date date NOT NULL,
    begin_date date NOT NULL,
    end_date date NOT NULL,
    belated_end_date date NOT NULL,
    CONSTRAINT semester_check CHECK ((premature_begin_date < begin_date)),
    CONSTRAINT semester_check1 CHECK ((begin_date < end_date)),
    CONSTRAINT semester_check2 CHECK ((end_date < belated_end_date)),
    CONSTRAINT semester_overdue_fine_check CHECK ((overdue_fine > 0)),
    CONSTRAINT semester_reduced_semester_contribution_check CHECK ((reduced_semester_contribution > 0)),
    CONSTRAINT semester_registration_fee_check CHECK ((registration_fee > 0)),
    CONSTRAINT semester_regular_semester_contribution_check CHECK ((regular_semester_contribution > 0))
);


ALTER TABLE public.semester OWNER TO vagrant;

--
-- Name: semester_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE semester_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.semester_id_seq OWNER TO vagrant;

--
-- Name: semester_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE semester_id_seq OWNED BY semester.id;


--
-- Name: server_host; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE server_host (
    id integer NOT NULL,
    name character varying(255)
);


ALTER TABLE public.server_host OWNER TO vagrant;

--
-- Name: server_net_device; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE server_net_device (
    id integer NOT NULL,
    switch_port_id integer
);


ALTER TABLE public.server_net_device OWNER TO vagrant;

--
-- Name: split; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE split (
    id integer NOT NULL,
    amount integer NOT NULL,
    account_id integer NOT NULL,
    transaction_id integer NOT NULL,
    CONSTRAINT split_amount_check CHECK ((amount <> 0))
);


ALTER TABLE public.split OWNER TO vagrant;

--
-- Name: split_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE split_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.split_id_seq OWNER TO vagrant;

--
-- Name: split_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE split_id_seq OWNED BY split.id;


--
-- Name: srv_record; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE srv_record (
    id integer NOT NULL,
    service character varying(255) NOT NULL,
    time_to_live integer,
    priority integer NOT NULL,
    weight integer NOT NULL,
    port integer NOT NULL,
    target character varying(255) NOT NULL
);


ALTER TABLE public.srv_record OWNER TO vagrant;

--
-- Name: subnet; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE subnet (
    id integer NOT NULL,
    address character varying(51) NOT NULL,
    gateway character varying(51) NOT NULL,
    dns_domain character varying,
    reserved_addresses integer NOT NULL,
    ip_type subnet_ip_type NOT NULL
);


ALTER TABLE public.subnet OWNER TO vagrant;

--
-- Name: subnet_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE subnet_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.subnet_id_seq OWNER TO vagrant;

--
-- Name: subnet_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE subnet_id_seq OWNED BY subnet.id;


--
-- Name: switch; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE switch (
    id integer NOT NULL,
    name character varying(127) NOT NULL,
    management_ip character varying(127) NOT NULL
);


ALTER TABLE public.switch OWNER TO vagrant;

--
-- Name: switch_net_device; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE switch_net_device (
    id integer NOT NULL
);


ALTER TABLE public.switch_net_device OWNER TO vagrant;

--
-- Name: switch_port; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE switch_port (
    id integer NOT NULL,
    switch_id integer NOT NULL
);


ALTER TABLE public.switch_port OWNER TO vagrant;

--
-- Name: traffic_group; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE traffic_group (
    id integer NOT NULL,
    traffic_limit bigint NOT NULL
);


ALTER TABLE public.traffic_group OWNER TO vagrant;

--
-- Name: traffic_volume; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE traffic_volume (
    id integer NOT NULL,
    size bigint NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    type traffic_types NOT NULL,
    ip_id integer NOT NULL
);


ALTER TABLE public.traffic_volume OWNER TO vagrant;

--
-- Name: traffic_volume_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE traffic_volume_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.traffic_volume_id_seq OWNER TO vagrant;

--
-- Name: traffic_volume_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE traffic_volume_id_seq OWNED BY traffic_volume.id;


--
-- Name: transaction; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE transaction (
    id integer NOT NULL,
    description text NOT NULL,
    author_id integer,
    transaction_date timestamp without time zone NOT NULL,
    valid_date date NOT NULL
);


ALTER TABLE public.transaction OWNER TO vagrant;

--
-- Name: transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE transaction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.transaction_id_seq OWNER TO vagrant;

--
-- Name: transaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE transaction_id_seq OWNED BY transaction.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE "user" (
    id integer NOT NULL,
    login character varying(40) NOT NULL,
    name character varying(255) NOT NULL,
    registration_date timestamp without time zone NOT NULL,
    passwd_hash character varying,
    email character varying(255),
    finance_account_id integer,
    room_id integer NOT NULL
);


ALTER TABLE public."user" OWNER TO vagrant;

--
-- Name: user_host; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE user_host (
    id integer NOT NULL
);


ALTER TABLE public.user_host OWNER TO vagrant;

--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_id_seq OWNER TO vagrant;

--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE user_id_seq OWNED BY "user".id;


--
-- Name: user_log_entry; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE user_log_entry (
    id integer NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.user_log_entry OWNER TO vagrant;

--
-- Name: user_net_device; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE user_net_device (
    id integer NOT NULL
);


ALTER TABLE public.user_net_device OWNER TO vagrant;

--
-- Name: vlan; Type: TABLE; Schema: public; Owner: vagrant; Tablespace: 
--

CREATE TABLE vlan (
    id integer NOT NULL,
    name character varying(127) NOT NULL,
    tag integer NOT NULL
);


ALTER TABLE public.vlan OWNER TO vagrant;

--
-- Name: vlan_id_seq; Type: SEQUENCE; Schema: public; Owner: vagrant
--

CREATE SEQUENCE vlan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.vlan_id_seq OWNER TO vagrant;

--
-- Name: vlan_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: vagrant
--

ALTER SEQUENCE vlan_id_seq OWNED BY vlan.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY dormitory ALTER COLUMN id SET DEFAULT nextval('dormitory_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY finance_account ALTER COLUMN id SET DEFAULT nextval('finance_account_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY "group" ALTER COLUMN id SET DEFAULT nextval('group_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY host ALTER COLUMN id SET DEFAULT nextval('host_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY ip ALTER COLUMN id SET DEFAULT nextval('ip_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY journal ALTER COLUMN id SET DEFAULT nextval('journal_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY journal_entry ALTER COLUMN id SET DEFAULT nextval('journal_entry_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY log_entry ALTER COLUMN id SET DEFAULT nextval('log_entry_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY membership ALTER COLUMN id SET DEFAULT nextval('membership_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY net_device ALTER COLUMN id SET DEFAULT nextval('net_device_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY port ALTER COLUMN id SET DEFAULT nextval('port_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY property ALTER COLUMN id SET DEFAULT nextval('property_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY record ALTER COLUMN id SET DEFAULT nextval('record_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY room ALTER COLUMN id SET DEFAULT nextval('room_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY semester ALTER COLUMN id SET DEFAULT nextval('semester_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY split ALTER COLUMN id SET DEFAULT nextval('split_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY subnet ALTER COLUMN id SET DEFAULT nextval('subnet_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY traffic_volume ALTER COLUMN id SET DEFAULT nextval('traffic_volume_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY transaction ALTER COLUMN id SET DEFAULT nextval('transaction_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY "user" ALTER COLUMN id SET DEFAULT nextval('user_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY vlan ALTER COLUMN id SET DEFAULT nextval('vlan_id_seq'::regclass);


--
-- Data for Name: a_record; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY a_record (id, name, time_to_live, address_id) FROM stdin;
\.


--
-- Data for Name: aaaa_record; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY aaaa_record (id, name, time_to_live, address_id) FROM stdin;
\.


--
-- Data for Name: association_dormitory_vlan; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY association_dormitory_vlan (dormitory_id, vlan_id) FROM stdin;
\.


--
-- Data for Name: association_subnet_vlan; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY association_subnet_vlan (subnet_id, vlan_id) FROM stdin;
\.


--
-- Data for Name: cname_record; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY cname_record (id, name, record_for_id) FROM stdin;
\.


--
-- Data for Name: destination_port; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY destination_port (id) FROM stdin;
\.


--
-- Data for Name: dormitory; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY dormitory (id, number, short_name, street) FROM stdin;
\.


--
-- Name: dormitory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('dormitory_id_seq', 1, false);


--
-- Data for Name: finance_account; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY finance_account (id, name, type) FROM stdin;
\.


--
-- Name: finance_account_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('finance_account_id_seq', 1, false);


--
-- Data for Name: group; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY "group" (id, name, type) FROM stdin;
\.


--
-- Name: group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('group_id_seq', 1, false);


--
-- Data for Name: host; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY host (id, type, user_id, room_id) FROM stdin;
\.


--
-- Name: host_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('host_id_seq', 1, false);


--
-- Data for Name: ip; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY ip (id, address, net_device_id, subnet_id) FROM stdin;
\.


--
-- Name: ip_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('ip_id_seq', 1, false);


--
-- Data for Name: journal; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY journal (id, name, bank, account_number, routing_number, iban, bic, hbci_url, finance_account_id) FROM stdin;
\.


--
-- Data for Name: journal_entry; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY journal_entry (id, journal_id, amount, description, original_description, other_account_number, other_routing_number, other_name, import_time, transaction_date, valid_date, transaction_id) FROM stdin;
\.


--
-- Name: journal_entry_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('journal_entry_id_seq', 1, false);


--
-- Name: journal_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('journal_id_seq', 1, false);


--
-- Data for Name: log_entry; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY log_entry (id, type, message, "timestamp", author_id) FROM stdin;
\.


--
-- Name: log_entry_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('log_entry_id_seq', 1, false);


--
-- Data for Name: membership; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY membership (id, start_date, end_date, group_id, user_id) FROM stdin;
\.


--
-- Name: membership_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('membership_id_seq', 1, false);


--
-- Data for Name: mx_record; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY mx_record (id, server, domain, priority) FROM stdin;
\.


--
-- Data for Name: net_device; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY net_device (id, type, mac, host_id) FROM stdin;
\.


--
-- Name: net_device_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('net_device_id_seq', 1, false);


--
-- Data for Name: ns_record; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY ns_record (id, domain, server, time_to_live) FROM stdin;
\.


--
-- Data for Name: patch_port; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY patch_port (id, destination_port_id, room_id) FROM stdin;
\.


--
-- Data for Name: phone_port; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY phone_port (id) FROM stdin;
\.


--
-- Data for Name: port; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY port (id, type, name) FROM stdin;
\.


--
-- Name: port_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('port_id_seq', 1, false);


--
-- Data for Name: property; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY property (id, name, granted, property_group_id) FROM stdin;
\.


--
-- Data for Name: property_group; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY property_group (id) FROM stdin;
\.


--
-- Name: property_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('property_id_seq', 1, false);


--
-- Data for Name: record; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY record (id, type, host_id) FROM stdin;
\.


--
-- Name: record_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('record_id_seq', 1, false);


--
-- Data for Name: room; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY room (id, number, level, inhabitable, dormitory_id) FROM stdin;
\.


--
-- Name: room_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('room_id_seq', 1, false);


--
-- Data for Name: room_log_entry; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY room_log_entry (id, room_id) FROM stdin;
\.


--
-- Data for Name: semester; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY semester (id, name, registration_fee, regular_semester_contribution, reduced_semester_contribution, overdue_fine, premature_begin_date, begin_date, end_date, belated_end_date) FROM stdin;
\.


--
-- Name: semester_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('semester_id_seq', 1, false);


--
-- Data for Name: server_host; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY server_host (id, name) FROM stdin;
\.


--
-- Data for Name: server_net_device; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY server_net_device (id, switch_port_id) FROM stdin;
\.


--
-- Data for Name: split; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY split (id, amount, account_id, transaction_id) FROM stdin;
\.


--
-- Name: split_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('split_id_seq', 1, false);


--
-- Data for Name: srv_record; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY srv_record (id, service, time_to_live, priority, weight, port, target) FROM stdin;
\.


--
-- Data for Name: subnet; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY subnet (id, address, gateway, dns_domain, reserved_addresses, ip_type) FROM stdin;
\.


--
-- Name: subnet_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('subnet_id_seq', 1, false);


--
-- Data for Name: switch; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY switch (id, name, management_ip) FROM stdin;
\.


--
-- Data for Name: switch_net_device; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY switch_net_device (id) FROM stdin;
\.


--
-- Data for Name: switch_port; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY switch_port (id, switch_id) FROM stdin;
\.


--
-- Data for Name: traffic_group; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY traffic_group (id, traffic_limit) FROM stdin;
\.


--
-- Data for Name: traffic_volume; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY traffic_volume (id, size, "timestamp", type, ip_id) FROM stdin;
\.


--
-- Name: traffic_volume_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('traffic_volume_id_seq', 1, false);


--
-- Data for Name: transaction; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY transaction (id, description, author_id, transaction_date, valid_date) FROM stdin;
\.


--
-- Name: transaction_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('transaction_id_seq', 1, false);


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY "user" (id, login, name, registration_date, passwd_hash, email, finance_account_id, room_id) FROM stdin;
\.


--
-- Data for Name: user_host; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY user_host (id) FROM stdin;
\.


--
-- Name: user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('user_id_seq', 1, false);


--
-- Data for Name: user_log_entry; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY user_log_entry (id, user_id) FROM stdin;
\.


--
-- Data for Name: user_net_device; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY user_net_device (id) FROM stdin;
\.


--
-- Data for Name: vlan; Type: TABLE DATA; Schema: public; Owner: vagrant
--

COPY vlan (id, name, tag) FROM stdin;
\.


--
-- Name: vlan_id_seq; Type: SEQUENCE SET; Schema: public; Owner: vagrant
--

SELECT pg_catalog.setval('vlan_id_seq', 1, false);


--
-- Name: a_record_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY a_record
    ADD CONSTRAINT a_record_pkey PRIMARY KEY (id);


--
-- Name: aaaa_record_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY aaaa_record
    ADD CONSTRAINT aaaa_record_pkey PRIMARY KEY (id);


--
-- Name: cname_record_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY cname_record
    ADD CONSTRAINT cname_record_pkey PRIMARY KEY (id);


--
-- Name: destination_port_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY destination_port
    ADD CONSTRAINT destination_port_pkey PRIMARY KEY (id);


--
-- Name: dormitory_number_key; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY dormitory
    ADD CONSTRAINT dormitory_number_key UNIQUE (number);


--
-- Name: dormitory_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY dormitory
    ADD CONSTRAINT dormitory_pkey PRIMARY KEY (id);


--
-- Name: dormitory_short_name_key; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY dormitory
    ADD CONSTRAINT dormitory_short_name_key UNIQUE (short_name);


--
-- Name: finance_account_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY finance_account
    ADD CONSTRAINT finance_account_pkey PRIMARY KEY (id);


--
-- Name: group_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY "group"
    ADD CONSTRAINT group_pkey PRIMARY KEY (id);


--
-- Name: host_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY host
    ADD CONSTRAINT host_pkey PRIMARY KEY (id);


--
-- Name: ip_address_key; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY ip
    ADD CONSTRAINT ip_address_key UNIQUE (address);


--
-- Name: ip_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY ip
    ADD CONSTRAINT ip_pkey PRIMARY KEY (id);


--
-- Name: journal_entry_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY journal_entry
    ADD CONSTRAINT journal_entry_pkey PRIMARY KEY (id);


--
-- Name: journal_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY journal
    ADD CONSTRAINT journal_pkey PRIMARY KEY (id);


--
-- Name: log_entry_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY log_entry
    ADD CONSTRAINT log_entry_pkey PRIMARY KEY (id);


--
-- Name: membership_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY membership
    ADD CONSTRAINT membership_pkey PRIMARY KEY (id);


--
-- Name: mx_record_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY mx_record
    ADD CONSTRAINT mx_record_pkey PRIMARY KEY (id);


--
-- Name: net_device_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY net_device
    ADD CONSTRAINT net_device_pkey PRIMARY KEY (id);


--
-- Name: ns_record_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY ns_record
    ADD CONSTRAINT ns_record_pkey PRIMARY KEY (id);


--
-- Name: patch_port_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY patch_port
    ADD CONSTRAINT patch_port_pkey PRIMARY KEY (id);


--
-- Name: phone_port_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY phone_port
    ADD CONSTRAINT phone_port_pkey PRIMARY KEY (id);


--
-- Name: port_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY port
    ADD CONSTRAINT port_pkey PRIMARY KEY (id);


--
-- Name: property_group_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY property_group
    ADD CONSTRAINT property_group_pkey PRIMARY KEY (id);


--
-- Name: property_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY property
    ADD CONSTRAINT property_pkey PRIMARY KEY (id);


--
-- Name: record_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY record
    ADD CONSTRAINT record_pkey PRIMARY KEY (id);


--
-- Name: room_log_entry_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY room_log_entry
    ADD CONSTRAINT room_log_entry_pkey PRIMARY KEY (id);


--
-- Name: room_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY room
    ADD CONSTRAINT room_pkey PRIMARY KEY (id);


--
-- Name: semester_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY semester
    ADD CONSTRAINT semester_pkey PRIMARY KEY (id);


--
-- Name: server_host_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY server_host
    ADD CONSTRAINT server_host_pkey PRIMARY KEY (id);


--
-- Name: server_net_device_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY server_net_device
    ADD CONSTRAINT server_net_device_pkey PRIMARY KEY (id);


--
-- Name: split_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY split
    ADD CONSTRAINT split_pkey PRIMARY KEY (id);


--
-- Name: srv_record_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY srv_record
    ADD CONSTRAINT srv_record_pkey PRIMARY KEY (id);


--
-- Name: subnet_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY subnet
    ADD CONSTRAINT subnet_pkey PRIMARY KEY (id);


--
-- Name: switch_net_device_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY switch_net_device
    ADD CONSTRAINT switch_net_device_pkey PRIMARY KEY (id);


--
-- Name: switch_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY switch
    ADD CONSTRAINT switch_pkey PRIMARY KEY (id);


--
-- Name: switch_port_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY switch_port
    ADD CONSTRAINT switch_port_pkey PRIMARY KEY (id);


--
-- Name: traffic_group_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY traffic_group
    ADD CONSTRAINT traffic_group_pkey PRIMARY KEY (id);


--
-- Name: traffic_volume_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY traffic_volume
    ADD CONSTRAINT traffic_volume_pkey PRIMARY KEY (id);


--
-- Name: transaction_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY transaction
    ADD CONSTRAINT transaction_pkey PRIMARY KEY (id);


--
-- Name: user_host_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY user_host
    ADD CONSTRAINT user_host_pkey PRIMARY KEY (id);


--
-- Name: user_log_entry_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY user_log_entry
    ADD CONSTRAINT user_log_entry_pkey PRIMARY KEY (id);


--
-- Name: user_login_key; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_login_key UNIQUE (login);


--
-- Name: user_net_device_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY user_net_device
    ADD CONSTRAINT user_net_device_pkey PRIMARY KEY (id);


--
-- Name: user_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: vlan_pkey; Type: CONSTRAINT; Schema: public; Owner: vagrant; Tablespace: 
--

ALTER TABLE ONLY vlan
    ADD CONSTRAINT vlan_pkey PRIMARY KEY (id);


--
-- Name: a_record_address_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY a_record
    ADD CONSTRAINT a_record_address_id_fkey FOREIGN KEY (address_id) REFERENCES ip(id) ON DELETE CASCADE;


--
-- Name: a_record_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY a_record
    ADD CONSTRAINT a_record_id_fkey FOREIGN KEY (id) REFERENCES record(id);


--
-- Name: aaaa_record_address_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY aaaa_record
    ADD CONSTRAINT aaaa_record_address_id_fkey FOREIGN KEY (address_id) REFERENCES ip(id) ON DELETE CASCADE;


--
-- Name: aaaa_record_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY aaaa_record
    ADD CONSTRAINT aaaa_record_id_fkey FOREIGN KEY (id) REFERENCES record(id);


--
-- Name: association_dormitory_vlan_dormitory_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY association_dormitory_vlan
    ADD CONSTRAINT association_dormitory_vlan_dormitory_id_fkey FOREIGN KEY (dormitory_id) REFERENCES dormitory(id);


--
-- Name: association_dormitory_vlan_vlan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY association_dormitory_vlan
    ADD CONSTRAINT association_dormitory_vlan_vlan_id_fkey FOREIGN KEY (vlan_id) REFERENCES vlan(id);


--
-- Name: association_subnet_vlan_subnet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY association_subnet_vlan
    ADD CONSTRAINT association_subnet_vlan_subnet_id_fkey FOREIGN KEY (subnet_id) REFERENCES subnet(id);


--
-- Name: association_subnet_vlan_vlan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY association_subnet_vlan
    ADD CONSTRAINT association_subnet_vlan_vlan_id_fkey FOREIGN KEY (vlan_id) REFERENCES vlan(id);


--
-- Name: cname_record_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY cname_record
    ADD CONSTRAINT cname_record_id_fkey FOREIGN KEY (id) REFERENCES record(id);


--
-- Name: cname_record_record_for_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY cname_record
    ADD CONSTRAINT cname_record_record_for_id_fkey FOREIGN KEY (record_for_id) REFERENCES record(id) ON DELETE CASCADE;


--
-- Name: destination_port_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY destination_port
    ADD CONSTRAINT destination_port_id_fkey FOREIGN KEY (id) REFERENCES port(id);


--
-- Name: host_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY host
    ADD CONSTRAINT host_room_id_fkey FOREIGN KEY (room_id) REFERENCES room(id);


--
-- Name: host_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY host
    ADD CONSTRAINT host_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: ip_net_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY ip
    ADD CONSTRAINT ip_net_device_id_fkey FOREIGN KEY (net_device_id) REFERENCES net_device(id) ON DELETE CASCADE;


--
-- Name: ip_subnet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY ip
    ADD CONSTRAINT ip_subnet_id_fkey FOREIGN KEY (subnet_id) REFERENCES subnet(id);


--
-- Name: journal_entry_journal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY journal_entry
    ADD CONSTRAINT journal_entry_journal_id_fkey FOREIGN KEY (journal_id) REFERENCES journal(id);


--
-- Name: journal_entry_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY journal_entry
    ADD CONSTRAINT journal_entry_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES transaction(id);


--
-- Name: journal_finance_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY journal
    ADD CONSTRAINT journal_finance_account_id_fkey FOREIGN KEY (finance_account_id) REFERENCES finance_account(id);


--
-- Name: log_entry_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY log_entry
    ADD CONSTRAINT log_entry_author_id_fkey FOREIGN KEY (author_id) REFERENCES "user"(id);


--
-- Name: membership_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY membership
    ADD CONSTRAINT membership_group_id_fkey FOREIGN KEY (group_id) REFERENCES "group"(id) ON DELETE CASCADE;


--
-- Name: membership_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY membership
    ADD CONSTRAINT membership_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE;


--
-- Name: mx_record_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY mx_record
    ADD CONSTRAINT mx_record_id_fkey FOREIGN KEY (id) REFERENCES record(id);


--
-- Name: net_device_host_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY net_device
    ADD CONSTRAINT net_device_host_id_fkey FOREIGN KEY (host_id) REFERENCES host(id) ON DELETE CASCADE;


--
-- Name: ns_record_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY ns_record
    ADD CONSTRAINT ns_record_id_fkey FOREIGN KEY (id) REFERENCES record(id);


--
-- Name: patch_port_destination_port_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY patch_port
    ADD CONSTRAINT patch_port_destination_port_id_fkey FOREIGN KEY (destination_port_id) REFERENCES destination_port(id);


--
-- Name: patch_port_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY patch_port
    ADD CONSTRAINT patch_port_id_fkey FOREIGN KEY (id) REFERENCES port(id);


--
-- Name: patch_port_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY patch_port
    ADD CONSTRAINT patch_port_room_id_fkey FOREIGN KEY (room_id) REFERENCES room(id);


--
-- Name: phone_port_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY phone_port
    ADD CONSTRAINT phone_port_id_fkey FOREIGN KEY (id) REFERENCES destination_port(id);


--
-- Name: property_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY property_group
    ADD CONSTRAINT property_group_id_fkey FOREIGN KEY (id) REFERENCES "group"(id);


--
-- Name: property_property_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY property
    ADD CONSTRAINT property_property_group_id_fkey FOREIGN KEY (property_group_id) REFERENCES property_group(id);


--
-- Name: record_host_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY record
    ADD CONSTRAINT record_host_id_fkey FOREIGN KEY (host_id) REFERENCES host(id) ON DELETE CASCADE;


--
-- Name: room_dormitory_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY room
    ADD CONSTRAINT room_dormitory_id_fkey FOREIGN KEY (dormitory_id) REFERENCES dormitory(id);


--
-- Name: room_log_entry_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY room_log_entry
    ADD CONSTRAINT room_log_entry_id_fkey FOREIGN KEY (id) REFERENCES log_entry(id);


--
-- Name: room_log_entry_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY room_log_entry
    ADD CONSTRAINT room_log_entry_room_id_fkey FOREIGN KEY (room_id) REFERENCES room(id);


--
-- Name: server_host_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY server_host
    ADD CONSTRAINT server_host_id_fkey FOREIGN KEY (id) REFERENCES host(id);


--
-- Name: server_net_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY server_net_device
    ADD CONSTRAINT server_net_device_id_fkey FOREIGN KEY (id) REFERENCES net_device(id);


--
-- Name: server_net_device_switch_port_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY server_net_device
    ADD CONSTRAINT server_net_device_switch_port_id_fkey FOREIGN KEY (switch_port_id) REFERENCES switch_port(id);


--
-- Name: split_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY split
    ADD CONSTRAINT split_account_id_fkey FOREIGN KEY (account_id) REFERENCES finance_account(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: split_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY split
    ADD CONSTRAINT split_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES transaction(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: srv_record_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY srv_record
    ADD CONSTRAINT srv_record_id_fkey FOREIGN KEY (id) REFERENCES record(id);


--
-- Name: switch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY switch
    ADD CONSTRAINT switch_id_fkey FOREIGN KEY (id) REFERENCES host(id);


--
-- Name: switch_net_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY switch_net_device
    ADD CONSTRAINT switch_net_device_id_fkey FOREIGN KEY (id) REFERENCES net_device(id);


--
-- Name: switch_port_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY switch_port
    ADD CONSTRAINT switch_port_id_fkey FOREIGN KEY (id) REFERENCES destination_port(id);


--
-- Name: switch_port_switch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY switch_port
    ADD CONSTRAINT switch_port_switch_id_fkey FOREIGN KEY (switch_id) REFERENCES switch(id);


--
-- Name: traffic_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY traffic_group
    ADD CONSTRAINT traffic_group_id_fkey FOREIGN KEY (id) REFERENCES "group"(id);


--
-- Name: traffic_volume_ip_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY traffic_volume
    ADD CONSTRAINT traffic_volume_ip_id_fkey FOREIGN KEY (ip_id) REFERENCES ip(id) ON DELETE CASCADE;


--
-- Name: transaction_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY transaction
    ADD CONSTRAINT transaction_author_id_fkey FOREIGN KEY (author_id) REFERENCES "user"(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: user_finance_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_finance_account_id_fkey FOREIGN KEY (finance_account_id) REFERENCES finance_account(id);


--
-- Name: user_host_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY user_host
    ADD CONSTRAINT user_host_id_fkey FOREIGN KEY (id) REFERENCES host(id);


--
-- Name: user_log_entry_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY user_log_entry
    ADD CONSTRAINT user_log_entry_id_fkey FOREIGN KEY (id) REFERENCES log_entry(id);


--
-- Name: user_log_entry_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY user_log_entry
    ADD CONSTRAINT user_log_entry_user_id_fkey FOREIGN KEY (user_id) REFERENCES "user"(id);


--
-- Name: user_net_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY user_net_device
    ADD CONSTRAINT user_net_device_id_fkey FOREIGN KEY (id) REFERENCES net_device(id);


--
-- Name: user_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: vagrant
--

ALTER TABLE ONLY "user"
    ADD CONSTRAINT user_room_id_fkey FOREIGN KEY (room_id) REFERENCES room(id);


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

