import { useFeed } from '../lib/useFeed'

const TABS = [
  { key: 'connected', label: 'Warm' },
  { key: 'all', label: 'All new' },
  { key: 'interested', label: 'Interested' },
  { key: 'applied', label: 'Applied' },
]

function heat(strength) {
  if (strength == null) return 'none'
  if (strength >= 11) return 'hot'
  if (strength >= 9) return 'warm'
  return 'mild'
}

function ago(date) {
  if (!date) return ''
  const days = Math.round((Date.now() - new Date(date).getTime()) / 86400000)
  if (days <= 0) return 'today'
  if (days === 1) return 'yesterday'
  return `${days}d ago`
}

function Connection({ row }) {
  if (!row.contact_name) {
    return <div className="conn conn-none">no connection</div>
  }
  const others = (row.contacts_at_company || 1) - 1
  return (
    <div className="conn">
      <span className={`dot dot-${heat(row.strength)}`} />
      <div>
        <div className="conn-name">
          {row.contact_linkedin_url ? (
            <a href={row.contact_linkedin_url} target="_blank" rel="noreferrer">
              {row.contact_name}
            </a>
          ) : row.contact_name}
          {row.contact_role && <span className="conn-role"> · {row.contact_role}</span>}
        </div>
        <div className="conn-meta">
          via {row.source_label || row.source_name}
          {others > 0 && ` · +${others} more here`}
          {row.confidence === 'fuzzy' && ' · fuzzy match'}
        </div>
      </div>
    </div>
  )
}

export function Feed({ tab, setTab }) {
  const { rows, loading, error, setStatus } = useFeed(tab)

  return (
    <>
      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`tab ${tab === t.key ? 'is-active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {error && <div className="error">{error}</div>}
      {loading && <div className="muted pad">loading…</div>}
      {!loading && !rows.length && (
        <div className="empty">
          <p>Nothing here.</p>
          <p className="muted">
            {tab === 'connected'
              ? 'No new postings at a company where you know someone.'
              : 'Run the scraper, or import a connections file.'}
          </p>
        </div>
      )}

      <ul className="cards">
        {rows.map((row) => (
          <li key={row.id} className={`card card-${heat(row.strength)}`}>
            <div className="card-head">
              <a className="card-title" href={row.url} target="_blank" rel="noreferrer">
                {row.title}
              </a>
              {row.strength != null && (
                <span className="score" title="intro strength">
                  {row.strength.toFixed(1)}
                </span>
              )}
            </div>
            <div className="card-sub">
              {row.company_raw}
              {row.location && <span className="muted"> · {row.location}</span>}
              {row.posted_on && <span className="muted"> · {ago(row.posted_on)}</span>}
            </div>

            <Connection row={row} />

            <div className="actions">
              {row.status !== 'interested' && (
                <button onClick={() => setStatus(row.id, 'interested')}>Interested</button>
              )}
              {row.status !== 'applied' && (
                <button onClick={() => setStatus(row.id, 'applied')}>Applied</button>
              )}
              {row.status !== 'skipped' && (
                <button className="ghost" onClick={() => setStatus(row.id, 'skipped')}>
                  Skip
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </>
  )
}
