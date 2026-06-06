-- Trang thai ngan hang (vd. LOI_BANK khi bam "Loi Bank" tren UI chuyen khoan).

alter table public.zalo_contacts
  add column if not exists status_bank text null;

comment on column public.zalo_contacts.status_bank is
  'Trang thai xu ly NH; LOI_BANK = danh dau loi thong tin ngan hang.';

create index if not exists zalo_contacts_status_bank_idx
  on public.zalo_contacts (status_bank)
  where status_bank is not null;
