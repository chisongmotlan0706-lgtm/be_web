-- Bảng lưu báo cáo hoa hồng Shopee đã gộp theo ID đơn hàng (một dòng = một đơn).
-- Chạy SQL này trong Supabase SQL Editor (hoặc qua migration CLI).

create table if not exists public.affiliate_commission_orders (
  id uuid primary key default gen_random_uuid(),
  order_id text not null,
  order_status text not null,
  order_placed_at timestamptz not null,
  net_affiliate_commission numeric not null,
  sub_id1 text,
  source_filename text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint affiliate_commission_orders_order_id_key unique (order_id)
);

create index if not exists affiliate_commission_orders_order_placed_at_idx
  on public.affiliate_commission_orders (order_placed_at desc);

comment on table public.affiliate_commission_orders is
  'Dữ liệu import từ báo cáo hoa hồng; net_affiliate_commission là tổng theo đơn sau khi gộp các dòng item.';

-- Gợi ý: bật RLS + policy phù hợp nếu expose anon key ra client. Import nên đi qua backend với service_role.

create or replace function public.set_affiliate_commission_orders_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_affiliate_commission_orders_updated on public.affiliate_commission_orders;
create trigger trg_affiliate_commission_orders_updated
  before update on public.affiliate_commission_orders
  for each row
  execute procedure public.set_affiliate_commission_orders_updated_at();
