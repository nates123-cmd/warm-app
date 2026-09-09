import { useCallback, useEffect, useState } from 'react'
import { supabase } from './supabase'

// Mirrors tools/fit.py. Calibrated against jobs the user had already saved.
export const STRONG = 65
export const WORTH = 48

export function fitBand(fit) {
  if (fit == null) return null
  if (fit >= STRONG) return 'strong'
  if (fit >= WORTH) return 'worth'
  return 'weak'
}

export function useFeed(tab) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    let q = supabase.from('warm_feed').select('*').limit(300)

    if (tab === 'best') {
      // Both axes at once: someone you know, and a job worth wanting.
      q = q.eq('status', 'new').not('contact_name', 'is', null).gte('fit', WORTH)
    } else if (tab === 'warm') {
      q = q.eq('status', 'new').not('contact_name', 'is', null)
    } else if (tab === 'fit') {
      q = q.eq('status', 'new').gte('fit', STRONG)
    } else if (tab === 'all') {
      q = q.eq('status', 'new')
    } else {
      q = q.eq('status', tab)
    }

    // Warm-first tabs rank by introduction strength; the rest by fit.
    if (tab === 'warm' || tab === 'best') {
      q = q.order('strength', { ascending: false, nullsFirst: false })
           .order('fit', { ascending: false, nullsFirst: false })
    } else {
      q = q.order('fit', { ascending: false, nullsFirst: false })
           .order('posted_on', { ascending: false, nullsFirst: false })
    }

    const { data, error } = await q
    if (error) setError(error.message)
    else { setRows(data || []); setError(null) }
    setLoading(false)
  }, [tab])

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
