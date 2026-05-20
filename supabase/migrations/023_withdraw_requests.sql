-- Yeu cau rut / da chuyen khoan — ghi sau khi chot file da CK.

create table if not exists public.withdraw_requests (
  id uuid not null default gen_random_uuid(),
  id_from text not null,
  d_name text null,
  amount numeric not null,
  bank_type text not null,
  stk text not null,
  bank_name text not null,
  status text not null default 'PENDING'::text,
  note text null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint withdraw_requests_pkey primary key (id),
  constraint withdraw_requests_amount_check check ((amount > (0)::numeric))
);

create unique index if not exists uq_withdraw_one_pending_per_user
  on public.withdraw_requests using btree (id_from)
  where (status = 'PENDING'::text);

create index if not exists withdraw_requests_id_from_idx
  on public.withdraw_requests using btree (id_from);

create index if not exists withdraw_requests_status_idx
  on public.withdraw_requests using btree (status);

create or replace function public.set_withdraw_requests_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_withdraw_requests_updated on public.withdraw_requests;
create trigger trg_withdraw_requests_updated
  before update on public.withdraw_requests
  for each row
  execute procedure public.set_withdraw_requests_updated_at();

alter table public.withdraw_requests disable row level security;

grant select, insert, update, delete on table public.withdraw_requests to service_role;
grant select, insert, update, delete on table public.withdraw_requests to authenticated;

comment on table public.withdraw_requests is
  'Lich su yeu cau rut; sau chot CK ghi status CHUA_BAO_KHACH.';
