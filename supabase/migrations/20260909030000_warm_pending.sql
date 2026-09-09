-- Config staged before someone has an account.
--
-- Supabase only creates the auth user when they first sign in, so a profile
-- cannot be attached ahead of time. Staging it by email lets the app claim it
-- on their first visit — no second step by whoever set them up.

create table if not exists warm_pending_profiles (
  email         text primary key,
  display_name  text,
  queries       jsonb not null default '[]'::jsonb,
  fit_criteria  jsonb not null default '{}'::jsonb,
  created_at    timestamptz not null default now()
);

alter table warm_pending_profiles enable row level security;

-- Readable and removable only by the person whose address it is. Nobody can
-- enumerate the table, and the anon role gets nothing.
drop policy if exists warm_pending_own_read on warm_pending_profiles;
create policy warm_pending_own_read on warm_pending_profiles
  for select to authenticated
  using (lower(email) = lower(auth.jwt() ->> 'email'));

drop policy if exists warm_pending_own_delete on warm_pending_profiles;
create policy warm_pending_own_delete on warm_pending_profiles
  for delete to authenticated
  using (lower(email) = lower(auth.jwt() ->> 'email'));
