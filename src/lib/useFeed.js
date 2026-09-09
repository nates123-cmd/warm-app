import { useCallback, useEffect, useState } from 'react'
import { supabase } from './supabase'

export function useFeed(status) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    let q = supabase
      .from('warm_feed')
      .select('*')
      .order('strength', { ascending: false, nullsFirst: false })
      .order('posted_on', { ascending: false, nullsFirst: false })
      .limit(300)
    if (status === 'connected') q = q.eq('status', 'new').not('contact_name', 'is', null)
    else if (status === 'all') q = q.eq('status', 'new')
    else q = q.eq('status', status)

    const { data, error } = await q
    if (error) setError(error.message)
    else { setRows(data || []); setError(null) }
    setLoading(false)
  }, [status])

  useEffect(() => { load() }, [load])

  const setStatus = useCallback(async (id, next) => {
    setRows((prev) => prev.filter((r) => r.id !== id))
    const { error } = await supabase
      .from('warm_jobs')
      .update({ status: next, status_at: new Date().toISOString() })
      .eq('id', id)
    if (error) { setError(error.message); load() }
  }, [load])

  return { rows, loading, error, reload: load, setStatus }
}
