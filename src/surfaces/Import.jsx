import { useRef, useState } from 'react'
import { parseContactsCsv } from '../lib/parseContacts'
import { uploadContacts } from '../lib/importContacts'

export function Import({ ownerId, onDone }) {
  const [preview, setPreview] = useState(null)
  const [source, setSource] = useState('')
  const [isMine, setIsMine] = useState(false)
  const [busy, setBusy] = useState(null)
  const [done, setDone] = useState(null)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const handleFile = async (file) => {
    if (!file) return
    setError(null); setDone(null)
    try {
      const text = await file.text()
      const guess = file.name.replace(/\.[^.]+$/, '').split(/[_\-\s]/)[0].toLowerCase()
      const result = parseContactsCsv(text, guess)
      setSource((s) => s || guess)
      setPreview({ ...result, fileName: file.name })
    } catch (e) {
      setError(e.message)
    }
  }

  const save = async () => {
    if (!preview || !source.trim()) return
    setBusy('starting'); setError(null)
    try {
      const records = preview.records.map((r) => ({ ...r, source: source.trim() }))
      const res = await uploadContacts({
        source: source.trim(),
        trust: isMine ? 1.5 : 1.0,
        records,
        ownerId,
        onProgress: setBusy,
      })
      setDone(res); setPreview(null); onDone?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="pad">
      <h2>Import connections</h2>
      <p className="muted">
        Ask a trusted contact for <strong>Settings → Data Privacy → Get a copy of
        your data → Connections</strong>, then drop the CSV here. Sales Navigator
        scrapes work too.
      </p>

      <div
        className="drop"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); handleFile(e.dataTransfer.files[0]) }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          hidden
          onChange={(e) => handleFile(e.target.files[0])}
        />
        Drop a CSV, or tap to choose
      </div>

      {error && <div className="error">{error}</div>}

      {done && (
        <div className="ok">
          Imported {done.contacts} contacts and {done.affiliations} affiliations.
        </div>
      )}

      {preview && (
        <div className="preview">
          <div className="preview-file">{preview.fileName} · {preview.shape}</div>
          <dl className="stats">
            <div><dt>people</dt><dd>{preview.people}</dd></div>
            <div><dt>affiliations</dt><dd>{preview.records.length}</dd></div>
            <div><dt>companies</dt><dd>{preview.companies}</dd></div>
            <div><dt>no company</dt><dd className="muted">{preview.noCompany}</dd></div>
          </dl>

          <label className="field">
            <span>Whose network is this?</span>
            <input
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="joyce"
            />
          </label>
          <label className="check">
            <input type="checkbox" checked={isMine} onChange={(e) => setIsMine(e.target.checked)} />
            These are my own connections (ranks higher — direct ask)
          </label>

          <button className="primary" onClick={save} disabled={!!busy || !source.trim()}>
            {busy ? `${busy}…` : 'Import'}
          </button>

          {preview.records.length > 0 && (
            <table className="sample">
              <tbody>
                {preview.records.slice(0, 6).map((r, i) => (
                  <tr key={i}>
                    <td>{r.full_name}</td>
                    <td className="muted">{r.role || '—'}</td>
                    <td>{r.company_raw}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
