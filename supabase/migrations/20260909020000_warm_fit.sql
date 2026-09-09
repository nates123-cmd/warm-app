-- Fit scoring: is this the right job, independent of who you know there.
--
-- Warmth and fit are separate axes. A posting can be one, both or neither, and
-- the pair that matters most is both at once.

alter table warm_jobs add column if not exists description       text;
alter table warm_jobs add column if not exists seniority_level   text;
alter table warm_jobs add column if not exists employment_type   text;
alter table warm_jobs add column if not exists job_function      text;
alter table warm_jobs add column if not exists industries        text;
alter table warm_jobs add column if not exists salary_min        int;
alter table warm_jobs add column if not exists salary_max        int;
alter table warm_jobs add column if not exists workplace         text;  -- remote|hybrid|onsite
alter table warm_jobs add column if not exists fit               int;
alter table warm_jobs add column if not exists fit_reasons       jsonb;
alter table warm_jobs add column if not exists enriched_at       timestamptz;

create index if not exists warm_jobs_fit_idx
  on warm_jobs (owner_id, status, fit desc nulls last);
create index if not exists warm_jobs_unenriched_idx
  on warm_jobs (owner_id, enriched_at) where enriched_at is null;

-- What "a good match" means for this person.
alter table warm_profiles add column if not exists fit_criteria jsonb
  not null default '{}'::jsonb;

drop view if exists warm_feed;
create view warm_feed with (security_invoker = on) as
select
  j.id, j.owner_id, j.linkedin_job_id, j.title, j.company_raw, j.company_slug,
  j.location, j.url, j.posted_on, j.first_seen, j.status, j.note, j.query_label,
  j.digest_sent_at,
  j.seniority_level, j.employment_type, j.job_function, j.industries,
  j.salary_min, j.salary_max, j.workplace, j.fit, j.fit_reasons, j.enriched_at,
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
