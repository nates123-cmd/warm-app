// Must stay in lockstep with tools/normalize.py. Both sides of the company
// match run this; if they drift, the join silently misses.

const TRAILING_NOISE = new Set([
  'inc', 'incorporated', 'llc', 'llp', 'lp', 'ltd', 'limited', 'corp',
  'corporation', 'co', 'company', 'plc', 'gmbh', 'ag', 'nv', 'bv', 'sa',
  'spa', 'pty', 'pte', 'holdings', 'holding', 'group', 'international',
  'worldwide', 'global', 'usa', 'us',
])

const LEADING_NOISE = new Set(['the'])

const stripAccents = (s) => s.normalize('NFKD').replace(/[̀-ͯ]/g, '')

export function normCompany(raw) {
  if (!raw) return ''
  let s = stripAccents(String(raw)).toLowerCase()
  s = s.replace(/\(.*?\)/g, ' ')
  s = s.split(/\s+[-|/,]\s+/)[0]
  s = s.replace(/&/g, ' and ')
  s = s.replace(/[^a-z0-9]+/g, ' ')
  const tokens = s.split(' ').filter(Boolean)
  while (tokens.length && LEADING_NOISE.has(tokens[0])) tokens.shift()
  while (tokens.length && TRAILING_NOISE.has(tokens[tokens.length - 1])) tokens.pop()
  return tokens.join(' ')
}

export function normPerson(raw) {
  if (!raw) return ''
  let s = stripAccents(String(raw)).toLowerCase()
  s = s.split(',')[0]
  s = s.replace(/[^a-z0-9]+/g, ' ')
  return s.split(' ').filter(Boolean).join(' ')
}

const SENIORITY = [
  [/\b(founder|co-?founder|owner)\b/i, 5],
  [/\b(board|trustee|chair|chairperson|chairman)\b/i, 5],
  [/\b(ceo|coo|cfo|cto|cio|cmo|chief)\b/i, 4],
  [/\b(president|partner|managing director)\b/i, 4],
  [/\b(vp|vice president|svp|evp|head of|head)\b/i, 3],
  [/\b(director|principal)\b/i, 2],
  [/\b(manager|lead|senior)\b/i, 1],
]

export function seniority(role) {
  for (const [pattern, score] of SENIORITY) if (pattern.test(role || '')) return score
  return 0
}
