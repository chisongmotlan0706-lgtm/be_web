-- Remove snapshot table (missing-bank snapshot feature removed).

drop table if exists public.zalo_contacts_missing_bank_snapshots cascade;
