-- Lich su dong bo tien (HH -> zalo_contacts): moi dong = 1 contact trong 1 lan chay RPC.

create table if not exists public.commission_payout_sync_log (
  id uuid primary key default gen_random_uuid(),
  sync_batch_id uuid not null,
  id_from text not null,
  d_name text null,
  amount_added numeric not null,
  order_count int not null,
  available_amount_after numeric not null,
  created_at timestamptz not null default now()
);

create index if not exists commission_payout_sync_log_created_at_idx
  on public.commission_payout_sync_log (created_at desc);

create index if not exists commission_payout_sync_log_batch_idx
  on public.commission_payout_sync_log (sync_batch_id);

comment on table public.commission_payout_sync_log is
  'Ghi lai moi dong cong HH user (theo id_from) sau moi lan goi sync_commission_hh_to_zalo.';

-- Cap nhat RPC: ghi log + tra ve sync_batch_id trong JSON.

create or replace function public.sync_commission_hh_to_zalo()
returns jsonb
language sql
set search_path = public
as $$
  with batch as (
    select gen_random_uuid() as sync_batch_id
  ),
  skipped as (
    select count(*)::int as c
    from affiliate_commission_orders o
    where o.order_status = 'Hoàn thành'
      and (
        o.id_zl is null
        or btrim(o.id_zl) = ''
        or not exists (select 1 from zalo_contacts z where z.id_from = btrim(o.id_zl))
      )
  ),
  breakdown as (
    select btrim(o.id_zl) as id_zl,
           sum(coalesce(o.hh_user, 0)::numeric) as add_amt,
           count(*)::int as order_cnt
    from affiliate_commission_orders o
    inner join zalo_contacts z on z.id_from = btrim(o.id_zl)
    where o.order_status = 'Hoàn thành'
      and o.id_zl is not null
      and btrim(o.id_zl) <> ''
    group by btrim(o.id_zl)
  ),
  balance_done as (
    update zalo_contacts z
    set available_amount = coalesce(z.available_amount, 0) + b.add_amt
    from breakdown b
    where z.id_from = b.id_zl
    returning z.id_from, z.d_name, z.available_amount as new_bal, b.add_amt, b.order_cnt
  ),
  orders_done as (
    update affiliate_commission_orders o
    set order_status = 'Đã cộng tiền',
        order_status_transition = 'Hoàn thành -> Đã cộng tiền'
    from zalo_contacts z
    where z.id_from = btrim(o.id_zl)
      and o.order_status = 'Hoàn thành'
      and o.id_zl is not null
      and btrim(o.id_zl) <> ''
    returning o.id
  ),
  log_insert as (
    insert into public.commission_payout_sync_log (
      sync_batch_id,
      id_from,
      d_name,
      amount_added,
      order_count,
      available_amount_after
    )
    select b.sync_batch_id, bd.id_from, bd.d_name, bd.add_amt, bd.order_cnt, bd.new_bal
    from balance_done bd
    cross join batch b
    returning id
  )
  select jsonb_build_object(
    'sync_batch_id', (select batch.sync_batch_id::text from batch),
    'orders_updated', (select count(*)::int from orders_done),
    'orders_skipped_no_contact', (select s.c from skipped s),
    'contacts', coalesce(
      (
        select jsonb_agg(
          jsonb_build_object(
            'id_from', bd.id_from,
            'name', bd.d_name,
            'amount_added', bd.add_amt,
            'order_count', bd.order_cnt,
            'available_amount_after', bd.new_bal
          ) order by bd.id_from
        )
        from balance_done bd
      ),
      '[]'::jsonb
    ),
    'total_amount_added', coalesce((select sum(bd.add_amt) from balance_done bd), 0)
  );
$$;

comment on function public.sync_commission_hh_to_zalo() is
  'Cong hh_user don Hoan thanh vao zalo_contacts.available_amount; doi trang thai don; ghi commission_payout_sync_log.';

grant select, insert on public.commission_payout_sync_log to service_role;
grant select, insert on public.commission_payout_sync_log to authenticated;

-- Tranh loi RLS khi Supabase bat RLS mac dinh cho bang moi.
alter function public.sync_commission_hh_to_zalo()
  security definer
  set search_path = public;

alter table public.commission_payout_sync_log disable row level security;
