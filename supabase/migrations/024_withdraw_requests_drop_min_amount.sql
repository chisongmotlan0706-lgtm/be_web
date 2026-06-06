-- Bo nguong 50.000 VND; so tien theo file Excel / deduct_applied khi chot CK.

alter table public.withdraw_requests
  drop constraint if exists withdraw_requests_amount_check;

alter table public.withdraw_requests
  add constraint withdraw_requests_amount_check check ((amount > (0)::numeric));
