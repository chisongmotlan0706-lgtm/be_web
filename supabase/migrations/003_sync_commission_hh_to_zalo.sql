-- RPC: trong mot transaction cong hh_user (don Hoan thanh + co id_zl match zalo_contacts)
-- vao zalo_contacts.available_amount, roi doi order_status -> Da cong tien.
-- Can: zalo_contacts.available_amount, zalo_contacts.d_name, zalo_contacts.id_from.

create or replace function public.sync_commission_hh_to_zalo()
returns jsonb
language sql
set search_path = public
as $$
  with skipped as (
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
  )
  select jsonb_build_object(
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
  'Cong hh_user don Hoan thanh vao zalo_contacts.available_amount; doi trang thai don sang Da cong tien.';

grant execute on function public.sync_commission_hh_to_zalo() to service_role;
grant execute on function public.sync_commission_hh_to_zalo() to authenticated;
