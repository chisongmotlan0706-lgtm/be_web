-- Bang yeu cau rut duplicate (danh sach cho CK rieng).

create table if not exists public.withdraw_requests_duplicate (
  id uuid not null default gen_random_uuid(),
  id_from text null,
  d_name text null,
  amount numeric not null,
  bank_type text not null,
  stk text not null,
  bank_name text not null,
  status text not null default 'PENDING'::text,
  note text null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  id_global text null,
  constraint withdraw_requests_duplicate_pkey primary key (id),
  constraint withdraw_requests_duplicate_amount_check check ((amount > (0)::numeric)),
  constraint withdraw_requests_duplicate_amount_min_check check ((amount >= (50000)::numeric))
);

create index if not exists withdraw_requests_duplicate_id_from_idx
  on public.withdraw_requests_duplicate using btree (id_from);

create index if not exists withdraw_requests_duplicate_status_idx
  on public.withdraw_requests_duplicate using btree (status);

create index if not exists withdraw_requests_duplicate_id_global_idx
  on public.withdraw_requests_duplicate using btree (id_global);

create unique index if not exists withdraw_requests_duplicate_id_from_pending_uq
  on public.withdraw_requests_duplicate using btree (id_from)
  where (status = 'PENDING'::text);

create or replace function public.set_withdraw_requests_duplicate_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_withdraw_requests_duplicate_updated on public.withdraw_requests_duplicate;
create trigger trg_withdraw_requests_duplicate_updated
  before update on public.withdraw_requests_duplicate
  for each row
  execute procedure public.set_withdraw_requests_duplicate_updated_at();

alter table public.withdraw_requests_duplicate disable row level security;

grant select, insert, update, delete on table public.withdraw_requests_duplicate to service_role;
grant select, insert, update, delete on table public.withdraw_requests_duplicate to authenticated;

comment on table public.withdraw_requests_duplicate is
  'Yeu cau rut duplicate; PENDING = cho CK, COMPLETED = da xu ly.';
