-- Cot global cho import hoa hong / splits / convert (idempotent).

alter table public.auth_users
  add column if not exists id_globalzalo text null;

alter table public.convert_results
  add column if not exists id_globalzalo text null;
alter table public.convert_results
  add column if not exists id_globalgroup text null;

comment on column public.convert_results.id_globalzalo is 'ID Zalo global (bot map); sub_id1 file co the khop day.';
comment on column public.convert_results.id_globalgroup is 'ID nhom global (bot map); tra zalo_groups.id_global.';

alter table public.affiliate_commission_orders
  add column if not exists id_zl text null;
alter table public.affiliate_commission_orders
  add column if not exists name text null;
alter table public.affiliate_commission_orders
  add column if not exists hh_user numeric null;
alter table public.affiliate_commission_orders
  add column if not exists id_global text null;

alter table public.affiliate_commission_order_splits
  add column if not exists id_global text null;

alter table public.zalo_groups
  add column if not exists id_global text null;
alter table public.zalo_groups
  add column if not exists id_global_main text null;

alter table public.zalo_contacts
  add column if not exists id_global text null;
alter table public.zalo_contacts
  add column if not exists id_global_gr text null;
