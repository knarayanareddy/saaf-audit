// Lightweight subsequence fuzzy scorer. Returns a score (higher = better) or
// -Infinity when `query` is not a subsequence of `text`. Rewards word-start and
// consecutive matches, lightly penalises gaps.
export function fuzzyScore(query, text) {
  const q = (query || '').toLowerCase()
  const t = (text || '').toLowerCase()
  if (!q) return 0
  let ti = 0
  let score = 0
  let streak = 0
  let prev = -2
  for (let qi = 0; qi < q.length; qi++) {
    const c = q[qi]
    let found = -1
    for (let j = ti; j < t.length; j++) {
      if (t[j] === c) { found = j; break }
    }
    if (found === -1) return -Infinity
    const isWordStart = found === 0 || /[\s\-_/·.]/.test(t[found - 1])
    score += isWordStart ? 3 : 1
    if (found === prev + 1) { streak += 1; score += 2 * streak } else { streak = 0 }
    score -= (found - ti) * 0.05
    prev = found
    ti = found + 1
  }
  return score
}
