alter table public.auth_users
add column if not exists id_zl text null;

create unique index if not exists uq_auth_users_id_zl
  on public.auth_users (id_zl)
  where id_zl is not null;
