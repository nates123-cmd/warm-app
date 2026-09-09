import { useCallback, useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

/** Near-miss company names. One tap teaches the alias table permanently. */
export function Review({ ownerId }) {
  const [rows, setRows] = useState([])
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    const { data, error } = await supabase
      .from('warm_review_queue')
      .select('*')
      .order('score', { ascending: false })
    if (error) setError(error.message)
    else setRows(data || [])
  }, [])

  useEffect(() => { load() }, [load])

  const decide = async (row, same) => {
    setRows((prev) => prev.filter((r) => r.id !== row.id))
    if (same) {
      const { error } = await supabase.from('warm_company_aliases').upsert({
        owner_id: ownerId,
        alias_norm: row.job_company_norm,
        canonical_norm: row.candidate_norm,
      }, { onConflict: 'owner_id,alias_norm' })
      if (error) { setError(error.message); return }
    }
    await supabase.from('warm_review_queue').delete().eq('id', row.id)
  }

  return (
    <div className="pad">
      <h2>Company review</h2>
      <p className="muted">
        Names that nearly matched. Confirming one teaches it permanently, so the
        next scrape matches without asking.
      </p>
      {error && <div className="error">{error}</div>}
      {!rows.length && <div className="empty"><p className="muted">Nothing to review.</p></div>}
      <ul className="cards">
        {rows.map((r) => (
          <li key={r.id} className="card">
            <div className="card-sub">{r.title}</div>
            <div className="compare">
              <strong>{r.job_company}</strong>
              <span className="muted">is the same company as</span>
              <strong>{r.candidate_example}</strong>
              <span className="muted">
                {r.contact_count} contact{r.contact_count === 1 ? '' : 's'} · {Number(r.score).toFixed(2)}
              </span>
            </div>
            <div className="actions">
              <button onClick={() => decide(r, true)}>Same company</button>
              <button className="ghost" onClick={() => decide(r, false)}>Different</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
