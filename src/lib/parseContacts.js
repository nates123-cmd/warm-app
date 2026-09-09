// Browser port of tools/import_contacts.py.
//
// Five export shapes exist in the wild and they are heterogeneous *within* a
// single file: the company sometimes has its own column, sometimes only lives
// inside a newline blob, and is often absent entirely. So decide per row.
import { parseCsv } from './csv'
import { normCompany, normPerson, seniority } from './normalize'

const OFFICIAL = ['first name', 'last name', 'url']

function readRows(text) {
  const rows = parseCsv(text)
  for (let i = 0; i < rows.length; i++) {
    const low = rows[i].map((c) => (c || '').trim().toLowerCase())
    if (OFFICIAL.every((h, k) => low[k] === h)) {
      return { header: low, rows: rows.slice(i + 1) }
    }
  }
  return {
    header: (rows[0] || []).map((c) => (c || '').trim().toLowerCase()),
    rows: rows.slice(1),
  }
}

function splitBlob(cell) {
  const parts = (cell || '').split('\n').map((p) => p.trim()).filter(Boolean)
  if (parts.length >= 2) return { role: parts[0], company: parts[parts.length - 1] }
  return { role: parts[0] || '', company: '' }
}

function rowRecords(row, header) {
  const cells = row.map((c) => (c || '').trim())
  const idx = {}
  header.forEach((h, i) => { idx[h] = i })

  for (let i = cells.length - 1; i >= 1; i--) {
    if (cells[i].includes('\n')) {
      const { role, company } = splitBlob(cells[i])
      if (company) return [{ company, role }]
    }
  }
  const ci = idx.company
  if (ci !== undefined && cells[ci]) {
    const ri = idx.role
    return [{ company: cells[ci], role: ri !== undefined ? cells[ri] || '' : '' }]
  }
  if (cells.length >= 3 && cells[1] && !/^\d+$/.test(cells[1])) {
    return [{ company: cells[1], role: cells[2] || '' }]
  }
  return []
}

export function parseContactsCsv(text, source) {
  const { header, rows } = readRows(text)
  const official = OFFICIAL.every((h, k) => header[k] === h)
  const out = []
  let noCompany = 0
  let noName = 0

  for (const row of rows) {
    const col = (i) => (row[i] || '').trim()
    let name
    let url = ''
    let email = ''
    let recs

    if (official) {
      name = [col(0), col(1)].filter(Boolean).join(' ')
      url = col(2)
      email = col(3)
      recs = [{ company: col(4), role: col(5) }]
    } else {
      name = col(0)
      recs = rowRecords(row, header)
    }

    if (!name || !normPerson(name)) { noName++; continue }

    let emitted = false
    for (const { company, role } of recs) {
      const companyNorm = normCompany(company)
      if (!companyNorm) continue
      out.push({
        source,
        full_name: name,
        person_norm: normPerson(name),
        linkedin_url: url || null,
        email: email || null,
        company_raw: company,
        company_norm: companyNorm,
        role: role || null,
        seniority: seniority(role),
      })
      emitted = true
    }
    if (!emitted) noCompany++
  }

  return {
    shape: official ? 'official export' : 'scrape',
    records: out,
    people: new Set(out.map((r) => r.person_norm)).size,
    companies: new Set(out.map((r) => r.company_norm)).size,
    noCompany,
    noName,
  }
}
