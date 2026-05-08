-- Trang thai nhom (ACTIVE / INACTIVE / PENDING) cho man quan ly zalo_groups.

alter table public.zalo_groups
  add column if not exists status text;

comment on column public.zalo_groups.status is 'ACTIVE | INACTIVE | PENDING';
