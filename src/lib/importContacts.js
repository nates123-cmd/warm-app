import { supabase } from './supabase'

const CHUNK = 500

async function chunked(rows, fn) {
  for (let i = 0; i < rows.length; i += CHUNK) {
    const { error } = await fn(rows.slice(i, i + CHUNK))
    if (error) throw new Error(error.message)
  }
}

/** Upload one parsed CSV as a source + its contacts + their affiliations. */
export async function uploadContacts({ source, trust, records, ownerId, onProgress }) {
  onProgress?.('saving source')
  const { data: src, error: srcErr } = await supabase
    .from('warm_sources')
    .upsert({ owner_id: ownerId, name: source, trust }, { onConflict: 'owner_id,name' })
    .select('id')
    .single()
  if (srcErr) throw new Error(srcErr.message)

  // Collapse repeats inside the file; the same person recurs across board seats.
  const people = new Map()
  for (const r of records) {
    const prior = people.get(r.person_norm)
    if (!prior || (r.linkedin_url && !prior.linkedin_url)) {
      people.set(r.person_norm, {
        owner_id: ownerId,
        source_id: src.id,
        full_name: r.full_name,
        person_norm: r.person_norm,
        linkedin_url: r.linkedin_url,
        email: r.email,
      })
    }
  }

  onProgress?.(`saving ${people.size} contacts`)
  await chunked([...people.values()], (batch) =>
    supabase.from('warm_contacts').upsert(batch, { onConflict: 'owner_id,source_id,person_norm' })
  )

  onProgress?.('linking contacts')
  const { data: saved, error: readErr } = await supabase
    .from('warm_contacts')
    .select('id, person_norm')
    .eq('source_id', src.id)
  if (readErr) throw new Error(readErr.message)
  const idByPerson = new Map(saved.map((c) => [c.person_norm, c.id]))

  const affs = new Map()
  for (const r of records) {
    const contactId = idByPerson.get(r.person_norm)
    if (!contactId) continue
    const key = `${contactId}|${r.company_norm}`
    const prior = affs.get(key)
    if (!prior || r.seniority > prior.seniority) {
      affs.set(key, {
        owner_id: ownerId,
        contact_id: contactId,
        company_raw: r.company_raw,
        company_norm: r.company_norm,
        role: r.role,
        seniority: r.seniority,
      })
    }
  }

  onProgress?.(`saving ${affs.size} affiliations`)
  await chunked([...affs.values()], (batch) =>
    supabase.from('warm_affiliations').upsert(batch, { onConflict: 'owner_id,contact_id,company_norm' })
  )

  return { contacts: people.size, affiliations: affs.size }
}
