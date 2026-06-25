-- Run this in Supabase SQL editor after schema.sql
create or replace function due_urls()
returns table (
  id uuid,
  url text,
  label text,
  threshold_pct float
)
language sql
as $$
  select id, url, label, threshold_pct
  from monitored_urls
  where
    last_checked_at is null
    or last_checked_at < now() - (interval_hours || ' hours')::interval;
$$;
