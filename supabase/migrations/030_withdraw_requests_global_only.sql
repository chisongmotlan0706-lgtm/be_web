-- Chuan hoa withdraw_requests sang id_global (global-only).
-- Giu lai id_from de tuong thich du lieu cu, nhung bo rang buoc bat buoc/unique tren cot cu.

alter table public.withdraw_requests
  add column if not exists id_global text null;

-- Backfill id_global tu du lieu cu neu chua co.
update public.withdraw_requests
set id_global = nullif(btrim(id_from), '')
where (id_global is null or btrim(id_global) = '')
  and id_from is not null
  and btrim(id_from) <> '';

-- Khong bat buoc ghi id_from nua.
alter table public.withdraw_requests
  alter column id_from drop not null;

drop index if exists public.uq_withdraw_one_pending_per_user;
create unique index if not exists uq_withdraw_one_pending_per_user_global
  on public.withdraw_requests using btree (id_global)
  where (
    status = 'PENDING'::text
    and id_global is not null
    and btrim(id_global) <> ''
  );

drop index if exists public.withdraw_requests_id_from_idx;
create index if not exists withdraw_requests_id_global_idx
  on public.withdraw_requests using btree (id_global);

create index if not exists withdraw_requests_status_id_global_idx
  on public.withdraw_requests using btree (status, id_global);
