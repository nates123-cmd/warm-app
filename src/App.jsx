import { useEffect, useState } from 'react'
import { supabase } from './lib/supabase'
import { claimPendingProfile } from './lib/claimProfile'
import { Feed } from './surfaces/Feed'
import { Import } from './surfaces/Import'
import { Review } from './surfaces/Review'
import { Settings } from './surfaces/Settings'

const VIEWS = [
  { key: 'feed', label: 'Jobs' },
  { key: 'review', label: 'Review' },
  { key: 'import', label: 'Import' },
  { key: 'settings', label: 'Setup' },
]

export default function App() {
  const [view, setView] = useState('feed')
  const [tab, setTab] = useState('best')
  const [ownerId, setOwnerId] = useState(null)
  const [email, setEmail] = useState(null)
  const [reviewCount, setReviewCount] = useState(0)

  const [claimed, setClaimed] = useState(null)

  useEffect(() => {
    supabase.auth.getUser().then(async ({ data }) => {
      const id = data?.user?.id ?? null
      setOwnerId(id)
      setEmail(data?.user?.email ?? null)
      // Config staged before they had an account attaches itself here.
      const pending = await claimPendingProfile(id)
      if (pending) setClaimed(pending)
    })
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

      {/* Every app on this domain shares one session, so who you are signed in
          as is not obvious. Say it, and give a way out. */}
      <div className="whoami">
        <span className="muted">{email}</span>
        <button
          className="signout"
          onClick={async () => {
            await supabase.auth.signOut()
            window.location.reload()
          }}
        >
          sign out
        </button>
      </div>

      {claimed && (
        <div className="ok">
          Set up with {(claimed.queries || []).length} searches. Adjust them any
          time under Setup.
        </div>
      )}

      <main>
        {view === 'feed' && <Feed tab={tab} setTab={setTab} />}
        {view === 'review' && <Review ownerId={ownerId} />}
        {view === 'import' && <Import ownerId={ownerId} />}
        {view === 'settings' && <Settings ownerId={ownerId} />}
      </main>
    </div>
  )
}
