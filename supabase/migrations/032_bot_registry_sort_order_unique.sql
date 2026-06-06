-- sort_order phai duy nhat trong bot_registry.

create unique index if not exists uq_bot_registry_sort_order
  on public.bot_registry (sort_order);
