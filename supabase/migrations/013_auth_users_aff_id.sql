alter table public.auth_users
add column if not exists aff_id text null;

create index if not exists idx_auth_users_aff_id
  on public.auth_users (aff_id);
