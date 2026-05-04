-- Phan tang hoa hong: splits (dai ly 15%, chu tool 25% net_affiliate_commission) gan voi don import.

create table if not exists public.affiliate_commission_order_splits (
  id uuid primary key default gen_random_uuid(),
  commission_order_id uuid not null
    references public.affiliate_commission_orders (id) on delete cascade,
  order_id text not null,
  split_role text not null,
  id_zl text not null,
  group_id text,
  payout_pct numeric not null,
  amount numeric not null,
  net_affiliate_commission_at_split numeric not null,
  order_status text not null,
  import_batch_id uuid not null,
  source_filename text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint affiliate_commission_order_splits_role_chk
    check (split_role in ('agency', 'platform_owner')),
  constraint affiliate_commission_order_splits_order_role_uniq
    unique (commission_order_id, split_role)
);

create index if not exists affiliate_commission_order_splits_order_id_idx
  on public.affiliate_commission_order_splits (order_id);

create index if not exists affiliate_commission_order_splits_id_zl_idx
  on public.affiliate_commission_order_splits (id_zl);

create index if not exists affiliate_commission_order_splits_import_batch_idx
  on public.affiliate_commission_order_splits (import_batch_id);

comment on table public.affiliate_commission_order_splits is
  'Phan bo hoa hong theo don import: agency (15% net) va platform_owner (25% net); order_status sync lan import cuoi.';

create or replace function public.set_affiliate_commission_order_splits_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_affiliate_commission_order_splits_updated
  on public.affiliate_commission_order_splits;
create trigger trg_affiliate_commission_order_splits_updated
  before update on public.affiliate_commission_order_splits
  for each row
  execute procedure public.set_affiliate_commission_order_splits_updated_at();
