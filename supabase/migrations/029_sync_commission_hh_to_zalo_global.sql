-- Bill Conversion / sync HH: chuyen sang id_global (khong phu thuoc id_zl legacy).
-- p_restrict_order_ids = NULL: dong bo tat ca don Hoan thanh du dieu kien.
-- p_restrict_order_ids = '{}': khong don nao duoc xu ly.

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
      btrim(o.id_global) as id_global_aff,
      coalesce(o.hh_user, 0)::numeric as hh
    from affiliate_commission_orders o
    where o.order_status = 'Hoàn thành'
      and o.id_global is not null
      and btrim(o.id_global) <> ''
      and exists (select 1 from zalo_contacts z where z.id_global = btrim(o.id_global))
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
        o.id_global is null
        or btrim(o.id_global) = ''
        or not exists (select 1 from zalo_contacts z where z.id_global = btrim(o.id_global))
      )
  ),
  aff_by_global as (
    select
      e.id_global_aff as id_global,
      sum(e.hh)::numeric as add_amt,
      count(*)::int as ord_cnt,
      0::int as spl_cnt
    from eligible e
    group by e.id_global_aff
  ),
  split_by_global as (
    select
      btrim(s.id_global) as id_global,
      sum(coalesce(s.amount, 0)::numeric) as add_amt,
      0::int as ord_cnt,
      count(*)::int as spl_cnt
    from affiliate_commission_order_splits s
    inner join eligible e on e.id = s.commission_order_id
    inner join zalo_contacts zr on zr.id_global = btrim(s.id_global)
    where s.id_global is not null
      and btrim(s.id_global) <> ''
    group by btrim(s.id_global)
  ),
  merged as (
    select id_global, add_amt, ord_cnt, spl_cnt from aff_by_global
    union all
    select id_global, add_amt, ord_cnt, spl_cnt from split_by_global
  ),
  breakdown as (
    select
      m.id_global,
      sum(m.add_amt)::numeric as add_amt,
      sum(m.ord_cnt + m.spl_cnt)::int as order_cnt
    from merged m
    group by m.id_global
  ),
  balance_done as (
    update zalo_contacts z
    set available_amount = coalesce(z.available_amount, 0) + b.add_amt
    from breakdown b
    where z.id_global = b.id_global
    returning
      z.id_global,
      z.id_from,
      z.d_name,
      z.available_amount as new_bal,
      b.add_amt,
      b.order_cnt
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
    select
      b.sync_batch_id,
      coalesce(nullif(bd.id_from, ''), bd.id_global),
      bd.d_name,
      bd.add_amt,
      bd.order_cnt,
      bd.new_bal
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
            'id_global', bd.id_global,
            'id_from', bd.id_from,
            'name', bd.d_name,
            'amount_added', bd.add_amt,
            'order_count', bd.order_cnt,
            'available_amount_after', bd.new_bal
          ) order by bd.id_global
        )
        from balance_done bd
      ),
      '[]'::jsonb
    ),
    'total_amount_added', coalesce((select sum(bd.add_amt) from balance_done bd), 0)
  );
$$;

comment on function public.sync_commission_hh_to_zalo(text[]) is
  'Dong bo HH user + splits theo id_global cho don Hoan thanh; p_restrict_order_ids NULL = tat ca.';

alter function public.sync_commission_hh_to_zalo(text[])
  security definer
  set search_path = public;

grant execute on function public.sync_commission_hh_to_zalo(text[]) to service_role;
grant execute on function public.sync_commission_hh_to_zalo(text[]) to authenticated;
