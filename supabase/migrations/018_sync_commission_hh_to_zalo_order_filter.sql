-- Them tham so tuy chon: chi dong bo don co order_id thuoc mang (file Bill Conversion).
-- p_restrict_order_ids = NULL: giu hanh vi cu (tat ca don Hoan thanh du dieu kien).
-- p_restrict_order_ids = '{}': khong don nao duoc xu ly.
-- Chi cap nhat trang thai don trong tap eligible (join theo id don).
-- Goi khong tham so: sync_commission_hh_to_zalo() tuong duong NULL.

drop function if exists public.sync_commission_hh_to_zalo();
drop function if exists public.sync_commission_hh_to_zalo(text[]);

create or replace function public.sync_commission_hh_to_zalo(p_restrict_order_ids text[] default null)
returns jsonb
language sql
set search_path = public
as $$
  with batch as (
    select gen_random_uuid() as sync_batch_id
  ),
  eligible as (
    select
      o.id,
      o.order_id,
      btrim(o.id_zl) as id_zl_aff,
      coalesce(o.hh_user, 0)::numeric as hh
    from affiliate_commission_orders o
    where o.order_status = 'Hoàn thành'
      and o.id_zl is not null
      and btrim(o.id_zl) <> ''
      and exists (select 1 from zalo_contacts z where z.id_from = btrim(o.id_zl))
      and (
        p_restrict_order_ids is null
        or o.order_id = any(p_restrict_order_ids)
      )
  ),
  skipped as (
    select count(*)::int as c
    from affiliate_commission_orders o
    where o.order_status = 'Hoàn thành'
      and (
        p_restrict_order_ids is null
        or o.order_id = any(p_restrict_order_ids)
      )
      and (
        o.id_zl is null
        or btrim(o.id_zl) = ''
        or not exists (select 1 from zalo_contacts z where z.id_from = btrim(o.id_zl))
      )
  ),
  aff_by_zl as (
    select
      e.id_zl_aff as id_zl,
      sum(e.hh)::numeric as add_amt,
      count(*)::int as ord_cnt,
      0::int as spl_cnt
    from eligible e
    group by e.id_zl_aff
  ),
  split_by_zl as (
    select
      btrim(s.id_zl) as id_zl,
      sum(coalesce(s.amount, 0)::numeric) as add_amt,
      0::int as ord_cnt,
      count(*)::int as spl_cnt
    from affiliate_commission_order_splits s
    inner join eligible e on e.id = s.commission_order_id
    inner join zalo_contacts zr on zr.id_from = btrim(s.id_zl)
    group by btrim(s.id_zl)
  ),
  merged as (
    select id_zl, add_amt, ord_cnt, spl_cnt from aff_by_zl
    union all
    select id_zl, add_amt, ord_cnt, spl_cnt from split_by_zl
  ),
  breakdown as (
    select
      m.id_zl,
      sum(m.add_amt)::numeric as add_amt,
      sum(m.ord_cnt + m.spl_cnt)::int as order_cnt
    from merged m
    group by m.id_zl
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
    from eligible e
    where o.id = e.id
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

comment on function public.sync_commission_hh_to_zalo(text[]) is
  'Cong hh_user + splits don Hoan thanh; ghi log. p_restrict_order_ids NULL = tat ca don du dieu kien; mang text = chi order_id trong mang.';

alter function public.sync_commission_hh_to_zalo(text[])
  security definer
  set search_path = public;

grant execute on function public.sync_commission_hh_to_zalo(text[]) to service_role;
grant execute on function public.sync_commission_hh_to_zalo(text[]) to authenticated;
