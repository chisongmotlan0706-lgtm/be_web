-- Cau hinh % phan tang cho splits: agency + platform_owner.
-- 1 dong duy nhat (id=1) de de quan ly tren UI.

create table if not exists public.commission_split_config (
  id smallint primary key default 1,
  agency_pct numeric not null,
  owner_pct numeric not null,
  updated_at timestamp with time zone not null default now(),
  constraint commission_split_config_singleton check (id = 1),
  constraint commission_split_config_agency_pct_range check (agency_pct >= 0 and agency_pct <= 100),
  constraint commission_split_config_owner_pct_range check (owner_pct >= 0 and owner_pct <= 100),
  constraint commission_split_config_sum_pct check (agency_pct + owner_pct <= 100)
);

insert into public.commission_split_config (id, agency_pct, owner_pct)
values (1, 15, 25)
on conflict (id) do nothing;

comment on table public.commission_split_config is
  '1 dong cau hinh % phan tang splits: agency_pct va owner_pct (platform_owner).';
comment on column public.commission_split_config.agency_pct is 'Percent cho dai ly (agency) tren net_affiliate_commission.';
comment on column public.commission_split_config.owner_pct is 'Percent cho chu tool (platform_owner) tren net_affiliate_commission.';
