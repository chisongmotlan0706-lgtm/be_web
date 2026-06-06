-- RPC insert bi chan boi RLS tren commission_payout_sync_log.
-- 1) Function chay voi quyen owner (bo qua RLS doi voi superuser/owner hop le).
-- 2) Tat RLS tren bang log (bang noi bo, chi ghi qua RPC / doc qua backend service_role).

alter function public.sync_commission_hh_to_zalo()
  security definer
  set search_path = public;

alter table public.commission_payout_sync_log disable row level security;
