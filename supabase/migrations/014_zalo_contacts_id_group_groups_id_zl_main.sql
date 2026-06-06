-- Lien ket contact -> nhom (id_group = group_id) va chu nhom (id_zl_main).

alter table public.zalo_groups
  add column if not exists id_zl_main text null;

alter table public.zalo_contacts
  add column if not exists id_group text null;

comment on column public.zalo_groups.id_zl_main is 'ID Zalo chu tool / owner nhom; khop voi auth user id_zl.';
comment on column public.zalo_contacts.id_group is 'group_id trong zalo_groups; mot contact thuoc mot nhom.';
