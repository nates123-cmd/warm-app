import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

const BLANK = { keywords: '', location: '' }

export function Settings({ ownerId }) {
  const [profile, setProfile] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!ownerId) return
    supabase
      .from('warm_profiles')
      .select('*')
      .eq('owner_id', ownerId)
      .maybeSingle()
      .then(({ data, error }) => {
        if (error) setError(error.message)
        setProfile(data || {
          owner_id: ownerId, display_name: '', queries: [{ ...BLANK }],
          telegram_chat_id: '', digest_enabled: true, active: true,
        })
      })
  }, [ownerId])

  if (!profile) return <div className="pad muted">loading…</div>

  const patch = (fields) => { setProfile((p) => ({ ...p, ...fields })); setSaved(false) }
  const queries = profile.queries?.length ? profile.queries : [{ ...BLANK }]

  const setQuery = (i, field, value) => {
    const next = queries.map((q, k) => (k === i ? { ...q, [field]: value } : q))
    patch({ queries: next })
  }

  const save = async () => {
    setSaving(true); setError(null)
    const clean = queries
      .map((q) => ({ keywords: q.keywords.trim(), location: q.location.trim() }))
      .filter((q) => q.keywords && q.location)
    const { error } = await supabase.from('warm_profiles').upsert({
      owner_id: ownerId,
      display_name: profile.display_name?.trim() || null,
      queries: clean,
      telegram_chat_id: profile.telegram_chat_id?.trim() || null,
      digest_enabled: !!profile.digest_enabled,
      active: true,
      updated_at: new Date().toISOString(),
    }, { onConflict: 'owner_id' })
    setSaving(false)
    if (error) setError(error.message)
    else { setSaved(true); patch({ queries: clean.length ? clean : [{ ...BLANK }] }) }
  }

  return (
    <div className="pad">
      <h2>What to look for</h2>
      <p className="muted">
        One row per job title and place. These run every morning; each search
        only pulls postings from the last 24 hours.
      </p>

      {error && <div className="error">{error}</div>}
      {saved && <div className="ok">Saved. Next run picks this up.</div>}

      <label className="field">
        <span>Your name</span>
        <input
          value={profile.display_name || ''}
          onChange={(e) => patch({ display_name: e.target.value })}
          placeholder="Alex"
        />
      </label>

      <div className="queries">
        {queries.map((q, i) => (
          <div className="query-row" key={i}>
            <input
              value={q.keywords}
              onChange={(e) => setQuery(i, 'keywords', e.target.value)}
              placeholder="Job title, e.g. Project Manager"
            />
            <input
              value={q.location}
              onChange={(e) => setQuery(i, 'location', e.target.value)}
              placeholder="New York, New York, United States"
            />
            <button
              className="ghost"
              aria-label="remove"
              onClick={() => patch({ queries: queries.filter((_, k) => k !== i) })}
            >
              ×
            </button>
          </div>
        ))}
      </div>
      <button className="ghost" onClick={() => patch({ queries: [...queries, { ...BLANK }] })}>
        + Add a search
      </button>

      <h2 style={{ marginTop: 28 }}>Daily message</h2>
      <label className="check">
        <input
          type="checkbox"
          checked={!!profile.digest_enabled}
          onChange={(e) => patch({ digest_enabled: e.target.checked })}
        />
        Send me a Telegram digest each morning
      </label>
      <label className="field" style={{ marginTop: 10 }}>
        <span>Telegram chat ID</span>
        <input
          value={profile.telegram_chat_id || ''}
          onChange={(e) => patch({ telegram_chat_id: e.target.value })}
          placeholder="message the bot once, then ask Nate for this"
        />
      </label>

      <button className="primary" onClick={save} disabled={saving}>
        {saving ? 'saving…' : 'Save'}
      </button>
    </div>
  )
}
