-- Ten hien thi cho value_1 .. value_5 (tuy chon, hien thi tren UI).

alter table public.app_config_kv
  add column if not exists label_1 text null,
  add column if not exists label_2 text null,
  add column if not exists label_3 text null,
  add column if not exists label_4 text null,
  add column if not exists label_5 text null;

comment on column public.app_config_kv.label_1 is 'Ten hien thi cho value_1.';
comment on column public.app_config_kv.label_2 is 'Ten hien thi cho value_2.';
comment on column public.app_config_kv.label_3 is 'Ten hien thi cho value_3.';
comment on column public.app_config_kv.label_4 is 'Ten hien thi cho value_4.';
comment on column public.app_config_kv.label_5 is 'Ten hien thi cho value_5.';
