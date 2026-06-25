-- Add URLs to monitor. Run in Supabase SQL editor.
insert into monitored_urls (url, label, interval_hours, threshold_pct) values
  ('https://example.com/pricing', 'Competitor A pricing', 24, 5.0),
  ('https://competitor.com/blog',  'Competitor B blog',   12, 3.0);
