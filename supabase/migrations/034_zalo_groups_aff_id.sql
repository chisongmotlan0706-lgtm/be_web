-- Gan aff_id (tu aff_bot.id_aff) cho nhom Zalo.

alter table public.zalo_groups
  add column if not exists aff_id text null;

create index if not exists idx_zalo_groups_aff_id
  on public.zalo_groups (aff_id)
  where aff_id is not null;

comment on column public.zalo_groups.aff_id is 'Ma affiliate chon tu bang aff_bot (id_aff).';
