-- Per-person configuration, so the daily job serves several job hunters at once
-- instead of one hard-coded owner id in the cron environment.

create table if not exists warm_profiles (
  owner_id         uuid primary key references auth.users(id) on delete cascade,
  display_name     text,
  -- [{"keywords": "Project Manager", "location": "New York, New York, United States"}]
  queries          jsonb not null default '[]'::jsonb,
  telegram_chat_id text,
  digest_enabled   boolean not null default true,
  active           boolean not null default true,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

alter table warm_profiles enable row level security;
drop policy if exists warm_profiles_owner on warm_profiles;
create policy warm_profiles_owner on warm_profiles for all to authenticated
  using (owner_id = auth.uid()) with check (owner_id = auth.uid());

-- A digest must never repeat a job, and triage state is separate from delivery.
alter table warm_jobs add column if not exists digest_sent_at timestamptz;
create index if not exists warm_jobs_undigested_idx
  on warm_jobs (owner_id, digest_sent_at) where digest_sent_at is null;

-- Rebuild the feed so the digest can filter on what it has already sent.
-- Must drop first: `create or replace view` cannot insert a column mid-list,
-- it tries to rename the existing one. security_invoker must also be restated.
drop view if exists warm_feed;
create view warm_feed with (security_invoker = on) as
select
  j.id, j.owner_id, j.linkedin_job_id, j.title, j.company_raw, j.company_slug,
  j.location, j.url, j.posted_on, j.first_seen, j.status, j.note, j.query_label,
  j.digest_sent_at,
  b.strength, b.confidence, b.contacts_at_company,
  c.full_name  as contact_name,
  c.linkedin_url as contact_linkedin_url,
  a.role       as contact_role,
  a.company_raw as contact_company,
  s.name       as source_name,
  s.label      as source_label
from warm_jobs j
left join lateral (
  select jc.* from warm_job_contacts jc
  where jc.job_id = j.id
  order by jc.strength desc
  limit 1
) b on true
left join warm_contacts c on c.id = b.contact_id
left join warm_sources  s on s.id = c.source_id
left join lateral (
  select af.* from warm_affiliations af
  where af.contact_id = c.id and af.company_norm = j.company_norm
  limit 1
) a on true;
