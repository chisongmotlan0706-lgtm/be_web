create extension if not exists pgcrypto;

create table if not exists public.auth_users (
  id uuid primary key default gen_random_uuid(),
  username text not null,
  password_hash text not null,
  is_active boolean not null default true,
  last_login_at timestamptz null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_auth_users_username unique (username),
  constraint ck_auth_users_username_not_blank check (length(trim(username)) > 0)
);

create index if not exists idx_auth_users_active on public.auth_users (is_active);

create table if not exists public.auth_refresh_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.auth_users(id) on delete cascade,
  token_hash text not null,
  expires_at timestamptz not null,
  revoked_at timestamptz null,
  created_at timestamptz not null default now(),
  created_ip text null,
  user_agent text null
);

create unique index if not exists uq_auth_refresh_tokens_token_hash
  on public.auth_refresh_tokens (token_hash);
create index if not exists idx_auth_refresh_tokens_user_id
  on public.auth_refresh_tokens (user_id);
create index if not exists idx_auth_refresh_tokens_expires_at
  on public.auth_refresh_tokens (expires_at);
create index if not exists idx_auth_refresh_tokens_revoked_at
  on public.auth_refresh_tokens (revoked_at);

grant usage on schema public to anon, authenticated;
grant select, insert, update, delete on table public.auth_users to authenticated;
grant select, insert, update, delete on table public.auth_refresh_tokens to authenticated;

alter table public.auth_users disable row level security;
alter table public.auth_refresh_tokens disable row level security;

insert into public.auth_users (username, password_hash, is_active)
values
  ('quangadmin', '$2b$12$oIp4VTCEKu37Uq6ERu6KsejgkPTrsbElvCv7Zelz9FdUrU422Bo7e', true),
  ('longadmin', '$2b$12$oIp4VTCEKu37Uq6ERu6KsejgkPTrsbElvCv7Zelz9FdUrU422Bo7e', true),
  ('trungadmin', '$2b$12$oIp4VTCEKu37Uq6ERu6KsejgkPTrsbElvCv7Zelz9FdUrU422Bo7e', true)
on conflict (username) do update
set
  password_hash = excluded.password_hash,
  is_active = excluded.is_active,
  updated_at = now();
