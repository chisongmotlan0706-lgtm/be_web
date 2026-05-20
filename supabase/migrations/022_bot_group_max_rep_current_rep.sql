-- Gioi han / dem REP cho nhom bot.

alter table public.bot_group
  add column if not exists max_rep bigint null,
  add column if not exists current_rep bigint null;

comment on column public.bot_group.max_rep is 'Nguong / gioi han REP (co the null). UI cho phep sua.';
comment on column public.bot_group.current_rep is 'REP hien tai (doc tu DB / job; UI chi xem, khong PUT).';
