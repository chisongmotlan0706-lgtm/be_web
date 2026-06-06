-- Import global-only: splits nhan tien theo id_global; id_zl legacy nullable.

alter table public.affiliate_commission_order_splits
  alter column id_zl drop not null;

comment on column public.affiliate_commission_order_splits.id_global is
  'ID Zalo global nguoi nhan split (agency / platform_owner).';
