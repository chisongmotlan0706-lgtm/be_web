-- Cột hien thi buoc doi trang thai: "cu -> moi" khi import thay doi order_status; neu khong doi thi NULL.
-- (Neu da chay ALTER TABLE thu cong thi file nay idempotent.)

alter table public.affiliate_commission_orders
  add column if not exists order_status_transition text;

comment on column public.affiliate_commission_orders.order_status_transition is
  'Chi ghi khi order_status doi giua hai lan import; order_status luon la trang thai moi tu file.';
