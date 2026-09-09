import { useState } from 'react'
import { fitBand, useFeed } from '../lib/useFeed'

const TABS = [
  { key: 'best', label: 'Best' },
  { key: 'warm', label: 'Warm' },
  { key: 'fit', label: 'Strong fit' },
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

function money(lo, hi) {
  if (!lo && !hi) return null
  const k = (n) => `$${Math.round(n / 1000)}k`
  return lo && hi ? `${k(lo)}–${k(hi)}` : k(lo || hi)
}

function Connection({ row }) {
  if (!row.contact_name) return null
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

function Why({ row }) {
  const [open, setOpen] = useState(false)
  const reasons = row.fit_reasons || []
  if (!reasons.length) return null
  return (
    <div className="why">
      <button className="why-toggle" onClick={() => setOpen((v) => !v)}>
        {open ? 'hide why' : 'why this scored'}
      </button>
      {open && (
        <ul className="why-list">
          {reasons.map((r, i) => <li key={i}>{r}</li>)}
        </ul>
      )}
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
            {tab === 'best' && 'No new job that is both a good fit and somewhere you know someone.'}
            {tab === 'warm' && 'No new postings where you know someone.'}
            {tab === 'fit' && 'No new postings that closely match what you are looking for.'}
            {tab === 'all' && 'Nothing new today. Check your searches under Setup.'}
            {(tab === 'interested' || tab === 'applied') && 'Nothing filed here yet.'}
          </p>
        </div>
      )}

      <ul className="cards">
        {rows.map((row) => {
          const fb = fitBand(row.fit)
          const pay = money(row.salary_min, row.salary_max)
          const both = row.contact_name && fb === 'strong'
          return (
            <li key={row.id} className={`card card-${heat(row.strength)}`}>
              <div className="card-head">
                <a className="card-title" href={row.url} target="_blank" rel="noreferrer">
                  {row.title}
                </a>
                {row.fit != null && (
                  <span className={`fit fit-${fb}`} title={`fit score ${row.fit}`}>
                    {row.fit}
                  </span>
                )}
              </div>

              <div className="card-sub">
                {row.company_raw}
                {row.location && <span className="muted"> · {row.location}</span>}
                {row.posted_on && <span className="muted"> · {ago(row.posted_on)}</span>}
              </div>

              <div className="chips">
                {both && <span className="chip chip-both">warm + strong fit</span>}
                {pay && <span className="chip">{pay}</span>}
                {row.workplace && <span className="chip">{row.workplace}</span>}
                {row.seniority_level && row.seniority_level !== 'Not Applicable' && (
                  <span className="chip">{row.seniority_level}</span>
                )}
              </div>

              <Connection row={row} />
              <Why row={row} />

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
          )
        })}
      </ul>
    </>
  )
}
