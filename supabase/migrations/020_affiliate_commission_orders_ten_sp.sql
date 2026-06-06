-- Ten san pham (gop theo order_id): JSON array string, vi du ["Ten SP 1","Ten SP 2"].

alter table public.affiliate_commission_orders
  add column if not exists ten_sp text null;

comment on column public.affiliate_commission_orders.ten_sp is
  'JSON array (text): danh sach Ten Item tu file import, gop theo order_id, bo trung, giu thu tu.';
