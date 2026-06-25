create table monitored_urls (
  id uuid primary key default gen_random_uuid(),
  url text not null unique,
  label text,
  interval_hours int not null default 24,
  threshold_pct float not null default 5.0,
  last_checked_at timestamptz,
  created_at timestamptz default now()
);

create table snapshots (
  id uuid primary key default gen_random_uuid(),
  url_id uuid not null references monitored_urls(id) on delete cascade,
  content text not null,
  content_hash text not null,
  change_pct float,
  checked_at timestamptz default now()
);

create index on snapshots(url_id, checked_at desc);
