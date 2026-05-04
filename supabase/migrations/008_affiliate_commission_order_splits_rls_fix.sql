-- Supabase co the bat RLS mac dinh cho bang moi -> insert/select bi chan.
alter table public.affiliate_commission_order_splits
  disable row level security;
