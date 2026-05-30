-- Chu nhom / dai ly tren nhom: id_globalzalo khop zalo_contacts.id_global.

alter table public.zalo_groups
  add column if not exists id_globalzalo text null;

comment on column public.zalo_groups.id_globalzalo is
  'ID Zalo global chu nhom (dai ly); khop zalo_contacts.id_global.';
