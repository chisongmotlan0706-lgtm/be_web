-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.affiliate_commission_orders (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  order_id text NOT NULL UNIQUE,
  order_status text NOT NULL,
  order_placed_at timestamp with time zone NOT NULL,
  net_affiliate_commission numeric NOT NULL,
  sub_id1 text,
  source_filename text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  id_zl text,
  name text,
  hh_user real,
  order_status_transition text,
  CONSTRAINT affiliate_commission_orders_pkey PRIMARY KEY (id)
);
CREATE TABLE public.commission_config (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  scope text NOT NULL DEFAULT 'global'::text,
  group_id text,
  id_from text,
  payout_pct real NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT commission_config_pkey PRIMARY KEY (id)
);
CREATE TABLE public.commission_payout_sync_log (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  sync_batch_id uuid NOT NULL,
  id_from text NOT NULL,
  d_name text,
  amount_added numeric NOT NULL,
  order_count integer NOT NULL,
  available_amount_after numeric NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT commission_payout_sync_log_pkey PRIMARY KEY (id)
);
CREATE TABLE public.convert_jobs (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  zl_id text NOT NULL,
  link_sp text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  zl text,
  group text,
  CONSTRAINT convert_jobs_pkey PRIMARY KEY (id)
);
CREATE TABLE public.convert_results (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  id_zl text NOT NULL,
  longlink text,
  source_job_id bigint,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  zl text,
  group text,
  price double precision,
  title text,
  spc_st text,
  trang_thai text,
  hoa_hong real,
  phan_tram_hh real,
  shortlink text,
  CONSTRAINT convert_results_pkey PRIMARY KEY (id)
);
CREATE TABLE public.zalo_contacts (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  id_from text NOT NULL,
  d_name text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  actual_amount double precision,
  estimated_amount double precision,
  stk text,
  bank_name text,
  available_amount double precision,
  bank_type text,
  received bigint,
  role text,
  CONSTRAINT zalo_contacts_pkey PRIMARY KEY (id)
);
CREATE TABLE public.zalo_groups (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  group_id text NOT NULL UNIQUE,
  id_zl text NOT NULL,
  group_name text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  deleted_at timestamp with time zone,
  CONSTRAINT zalo_groups_pkey PRIMARY KEY (id)
);