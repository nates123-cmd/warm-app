-- Warm: LinkedIn job postings ranked by who you already know there.
--
-- Matching runs in tools/ (Python, on the Beelink) so that normalization lives
-- in exactly one place; these tables store the result and the triage state.

create extension if not exists pgcrypto;

-- People whose network you are borrowing (yourself included).
create table if not exists warm_sources (
  id            uuid primary key default gen_random_uuid(),
  owner_id      uuid not null references auth.users(id) on delete cascade,
  name          text not null,
  label         text,
  -- Your own connections are a direct ask; a borrowed network needs a handoff.
  trust         numeric not null default 1.0,
  imported_at   timestamptz not null default now(),
  unique (owner_id, name)
);

create table if not exists warm_contacts (
  id            uuid primary key default gen_random_uuid(),
  owner_id      uuid not null references auth.users(id) on delete cascade,
  source_id     uuid not null references warm_sources(id) on delete cascade,
  full_name     text not null,
  person_norm   text not null,
  linkedin_url  text,
  email         text,
  created_at    timestamptz not null default now(),
  unique (owner_id, source_id, person_norm)
);

-- One contact, many companies: a mentor's board seats are the whole point.
create table if not exists warm_affiliations (
  id            uuid primary key default gen_random_uuid(),
  owner_id      uuid not null references auth.users(id) on delete cascade,
  contact_id    uuid not null references warm_contacts(id) on delete cascade,
  company_raw   text not null,
  company_norm  text not null,
  role          text,
  seniority     int not null default 0,
  unique (owner_id, contact_id, company_norm)
);
create index if not exists warm_affiliations_company_idx
  on warm_affiliations (owner_id, company_norm);

-- Learned company-name equivalences, taught by confirming a review row.
create table if not exists warm_company_aliases (
  owner_id       uuid not null references auth.users(id) on delete cascade,
  alias_norm     text not null,
  canonical_norm text not null,
  created_at     timestamptz not null default now(),
  primary key (owner_id, alias_norm)
);

create table if not exists warm_jobs (
  id               uuid primary key default gen_random_uuid(),
  owner_id         uuid not null references auth.users(id) on delete cascade,
  linkedin_job_id  text not null,
  title            text not null,
  company_raw      text,
  company_norm     text,
  company_slug     text,
  location         text,
  url              text,
  posted_on        date,
  query_label      text,
  first_seen       timestamptz not null default now(),
  status           text not null default 'new'
                   check (status in ('new','interested','skipped','applied')),
  status_at        timestamptz,
  note             text,
  unique (owner_id, linkedin_job_id)
);
create index if not exists warm_jobs_feed_idx
  on warm_jobs (owner_id, status, posted_on desc);

create table if not exists warm_job_contacts (
  owner_id            uuid not null references auth.users(id) on delete cascade,
  job_id              uuid not null references warm_jobs(id) on delete cascade,
  contact_id          uuid not null references warm_contacts(id) on delete cascade,
  strength            numeric not null default 0,
  confidence          text not null default 'exact',
  contacts_at_company int not null default 1,
  primary key (job_id, contact_id)
);
create index if not exists warm_job_contacts_job_idx
  on warm_job_contacts (owner_id, job_id, strength desc);

-- Near-miss company names awaiting one tap to confirm or reject.
create table if not exists warm_review_queue (
  id               uuid primary key default gen_random_uuid(),
  owner_id         uuid not null references auth.users(id) on delete cascade,
  job_company      text not null,
  job_company_norm text not null,
  candidate_norm   text not null,
  candidate_example text,
  contact_count    int not null default 0,
  score            numeric,
  created_at       timestamptz not null default now(),
  unique (owner_id, job_company_norm, candidate_norm)
);

alter table warm_sources          enable row level security;
alter table warm_contacts         enable row level security;
alter table warm_affiliations     enable row level security;
alter table warm_company_aliases  enable row level security;
alter table warm_jobs             enable row level security;
alter table warm_job_contacts     enable row level security;
alter table warm_review_queue     enable row level security;

do $$
declare t text;
begin
  foreach t in array array[
    'warm_sources','warm_contacts','warm_affiliations','warm_company_aliases',
    'warm_jobs','warm_job_contacts','warm_review_queue'
  ] loop
    execute format(
      'drop policy if exists %I on %I', t || '_owner', t);
    execute format(
      'create policy %I on %I for all to authenticated
         using (owner_id = auth.uid()) with check (owner_id = auth.uid())',
      t || '_owner', t);
  end loop;
end $$;

-- The feed the app reads: one row per job, with its strongest connection.
--
-- security_invoker is mandatory here: without it the view runs with definer
-- rights and hands every owner's rows to every caller, straight past RLS.
create or replace view warm_feed with (security_invoker = on) as
select
  j.id, j.owner_id, j.linkedin_job_id, j.title, j.company_raw, j.company_slug,
  j.location, j.url, j.posted_on, j.first_seen, j.status, j.note, j.query_label,
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
