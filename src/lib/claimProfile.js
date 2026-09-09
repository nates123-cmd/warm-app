import { supabase } from './supabase'

/** Attach any config staged for this person's email, once, on first sign-in.
 *
 * Supabase only creates the auth user at first sign-in, so whoever set them up
 * cannot attach a profile ahead of time. RLS on warm_pending_profiles limits
 * each row to the address it belongs to.
 */
export async function claimPendingProfile(ownerId) {
  if (!ownerId) return null

  const { data: existing } = await supabase
    .from('warm_profiles')
    .select('owner_id')
    .eq('owner_id', ownerId)
    .maybeSingle()
  if (existing) return null

  const { data: pending, error } = await supabase
    .from('warm_pending_profiles')
    .select('*')
    .limit(1)
    .maybeSingle()
  if (error || !pending) return null

  const { error: upsertErr } = await supabase.from('warm_profiles').upsert({
    owner_id: ownerId,
    display_name: pending.display_name,
    queries: pending.queries || [],
    fit_criteria: pending.fit_criteria || {},
    active: true,
  }, { onConflict: 'owner_id' })
  if (upsertErr) return null

  // Best-effort: a leftover row is harmless, since the profile now exists.
  await supabase.from('warm_pending_profiles').delete().eq('email', pending.email)
  return pending
}
