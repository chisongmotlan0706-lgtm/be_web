-- Cau hinh bot: bot_registry + reply_router_state (thay bot_group cho UI admin).

create table if not exists public.bot_registry (
  id_bot text not null,
  display_name text null,
  max_consecutive_replies integer not null default 5,
  sort_order integer not null default 0,
  is_enabled boolean not null default true,
  created_at timestamp with time zone not null default now(),
  constraint bot_registry_pkey primary key (id_bot),
  constraint bot_registry_max_consecutive_replies_check check ((max_consecutive_replies > 0))
);

create index if not exists idx_bot_registry_sort_order on public.bot_registry (sort_order asc, id_bot asc);

comment on table public.bot_registry is 'Danh sach bot: ten hien thi, gioi han reply lien tiep, bat/tat.';
comment on column public.bot_registry.max_consecutive_replies is 'So reply lien tiep toi da truoc khi chuyen bot.';
comment on column public.bot_registry.sort_order is 'Thu tu hien thi / uu tien trong danh sach.';

create table if not exists public.reply_router_state (
  scope_key text not null default 'global'::text,
  current_bot_id text not null,
  consecutive_used integer not null default 0,
  version bigint not null default 0,
  updated_at timestamp with time zone not null default now(),
  constraint reply_router_state_pkey primary key (scope_key),
  constraint reply_router_state_current_bot_id_fkey foreign key (current_bot_id) references public.bot_registry (id_bot),
  constraint reply_router_state_consecutive_used_check check ((consecutive_used >= 0))
);

comment on table public.reply_router_state is 'Trang thai router reply: bot hien tai va dem consecutive_used (chi doc tu UI admin).';

alter table public.bot_registry disable row level security;
alter table public.reply_router_state disable row level security;
