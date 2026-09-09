import { useEffect, useState } from 'react'
import { supabase } from './lib/supabase'
import { Feed } from './surfaces/Feed'
import { Import } from './surfaces/Import'
import { Review } from './surfaces/Review'

const VIEWS = [
  { key: 'feed', label: 'Jobs' },
  { key: 'review', label: 'Review' },
  { key: 'import', label: 'Import' },
]

export default function App() {
  const [view, setView] = useState('feed')
  const [tab, setTab] = useState('connected')
  const [ownerId, setOwnerId] = useState(null)
  const [reviewCount, setReviewCount] = useState(0)

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setOwnerId(data?.user?.id ?? null))
  }, [])

  useEffect(() => {
    supabase
      .from('warm_review_queue')
      .select('id', { count: 'exact', head: true })
      .then(({ count }) => setReviewCount(count || 0))
  }, [view])

  return (
    <div className="app">
      <header className="top">
        <h1>warm</h1>
        <nav className="views">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              className={`view ${view === v.key ? 'is-active' : ''}`}
              onClick={() => setView(v.key)}
            >
              {v.label}
              {v.key === 'review' && reviewCount > 0 && (
                <span className="badge">{reviewCount}</span>
              )}
            </button>
          ))}
        </nav>
      </header>

      <main>
        {view === 'feed' && <Feed tab={tab} setTab={setTab} />}
        {view === 'review' && <Review ownerId={ownerId} />}
        {view === 'import' && <Import ownerId={ownerId} />}
      </main>
    </div>
  )
}
