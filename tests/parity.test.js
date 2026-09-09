// The browser importer and the Beelink importer must agree. If these drift,
// company matching silently misses on whichever side is wrong.
import { readFileSync, existsSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { describe, expect, it } from 'vitest'
import { parseContactsCsv } from '../src/lib/parseContacts'
import { normCompany, normPerson } from '../src/lib/normalize'

const DOCS = '/Users/natestephenson/Downloads/Documents'
const FILES = [
  ['Connections.csv', 'nate'],
  ['Joyce_Linkedin_Connects___507018602.csv', 'joyce'],
  ['Gary_Sales_Nav__695747147.csv', 'gary'],
  ['job_nav_sales_nav_try_3___575036803.csv', 'salesnav3'],
]

const py = (code) =>
  execFileSync('python3', ['-c', code], { encoding: 'utf-8', maxBuffer: 64 * 1024 * 1024 })

describe('normalizer parity', () => {
  const cases = [
    'Google LLC', 'Google (YouTube)', 'The Rich Talent Group', 'Burns & McDonnell',
    'SiliconANGLE Media, Inc. - @theCUBE', 'Group Health', 'PwC', 'Acme - NE Region',
    'Crowell & Moring', 'AT&T Inc.', 'Ernst & Young LLP',
  ]
  it('matches tools/normalize.py on company names', () => {
    const expected = JSON.parse(py(`
import sys, json; sys.path.insert(0, 'tools')
from normalize import norm_company
print(json.dumps([norm_company(c) for c in ${JSON.stringify(cases)}]))
`))
    expect(cases.map(normCompany)).toEqual(expected)
  })

  it('matches tools/normalize.py on person names', () => {
    const names = ['Terry Doumkos, MBA', 'Sean K.', 'José Álvarez', 'Jane  Doe']
    const expected = JSON.parse(py(`
import sys, json; sys.path.insert(0, 'tools')
from normalize import norm_person
print(json.dumps([norm_person(c) for c in ${JSON.stringify(names)}]))
`))
    expect(names.map(normPerson)).toEqual(expected)
  })
})

describe('parser parity on real exports', () => {
  for (const [file, source] of FILES) {
    const path = `${DOCS}/${file}`
    const run = existsSync(path) ? it : it.skip
    run(`${file} yields the same affiliations as the python importer`, () => {
      const js = parseContactsCsv(readFileSync(path, 'utf-8'), source)
      const expected = JSON.parse(py(`
import sys, json; sys.path.insert(0, 'tools')
from import_contacts import parse
shape, recs, no_company, no_name = parse(${JSON.stringify(path)}, ${JSON.stringify(source)})
print(json.dumps({
  "count": len(recs),
  "people": len({r["person_norm"] for r in recs}),
  "companies": len({r["company_norm"] for r in recs}),
  "first": [[r["full_name"], r["company_norm"]] for r in recs[:25]],
}))
`))
      expect(js.records.length).toBe(expected.count)
      expect(js.people).toBe(expected.people)
      expect(js.companies).toBe(expected.companies)
      expect(js.records.slice(0, 25).map((r) => [r.full_name, r.company_norm]))
        .toEqual(expected.first)
    })
  }
})
