// Minimal RFC4180 reader. LinkedIn scrapes embed newlines inside quoted cells,
// so splitting on "\n" loses most of the file.
export function parseCsv(text) {
  const rows = []
  let row = []
  let field = ''
  let quoted = false
  let i = 0

  if (text.charCodeAt(0) === 0xfeff) i = 1 // strip BOM

  const endField = () => { row.push(field); field = '' }
  const endRow = () => { endField(); rows.push(row); row = [] }

  for (; i < text.length; i++) {
    const ch = text[i]
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') { field += '"'; i++ } else { quoted = false }
      } else field += ch
      continue
    }
    if (ch === '"') { quoted = true; continue }
    if (ch === ',') { endField(); continue }
    if (ch === '\r') continue
    if (ch === '\n') { endRow(); continue }
    field += ch
  }
  if (field !== '' || row.length) endRow()
  return rows.filter((r) => r.some((c) => (c || '').trim()))
}
