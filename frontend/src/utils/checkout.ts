import doubleOutTable from '../data/double_out_checkouts.json'

export interface CheckoutSuggestion {
  darts: string[]
  is_finish: boolean
  leave: number
  text: string
}

/**
 * Look up a double-out checkout suggestion from the pre-built table.
 * Covers remaining scores 1–170 with 1, 2, or 3 darts available.
 * Returns null if no valid finish exists for the given combination.
 */
export function getDoubleOutCheckout(
  remaining: number,
  dartsAvailable: number,
): CheckoutSuggestion | null {
  if (remaining <= 0 || remaining > 170 || dartsAvailable < 1 || dartsAvailable > 3) {
    return null
  }

  const entry = (doubleOutTable as string[][])[remaining]
  if (!entry) return null

  // Table layout per entry: [3-dart path, 2-dart path, 1-dart path, score]
  const pathStr = entry[3 - dartsAvailable]

  if (!pathStr || pathStr === '') {
    return null
  }

  const trimmed = pathStr.trim()

  // "No Finish" (bare) → truly unplayable
  if (trimmed === 'No Finish') {
    return null
  }

  // "No Finish (X)" → setup shot, not a finish
  const setupMatch = trimmed.match(/^No Finish \((.+)\)$/)
  if (setupMatch) {
    const dart = setupMatch[1]
    return { darts: [dart], is_finish: false, leave: -1, text: trimmed }
  }

  return {
    darts: trimmed.split(/\s+/),
    is_finish: true,
    leave: 0,
    text: trimmed,
  }
}

// ---------------------------------------------------------------------------
// Single-Out checkout suggestion (mirrors backend _single_out_suggestion)
// ---------------------------------------------------------------------------

/** Scores achievable in exactly one dart, with preferred label (single > Bull/Bullseye > triple > double). */
const _SINGLE_OUT_1DART: Map<number, string> = (() => {
  const result = new Map<number, string>()
  const candidates: [number, string][] = [
    ...Array.from({ length: 20 }, (_, i): [number, string] => [i + 1, String(i + 1)]),
    [25, 'Bull'],
    [50, 'Bullseye'],
    ...Array.from({ length: 20 }, (_, i): [number, string] => [(i + 1) * 3, `T${i + 1}`]),
    ...Array.from({ length: 20 }, (_, i): [number, string] => [(i + 1) * 2, `D${i + 1}`]),
  ]
  for (const [score, label] of candidates) {
    if (!result.has(score)) result.set(score, label)
  }
  return result
})()

/** All achievable dart scores, sorted descending (for greedy search). */
const _ALL_SCORES_DESC: number[] = (() => {
  const all = new Set<number>([
    ...Array.from({ length: 20 }, (_, i) => i + 1),
    25,
    ...Array.from({ length: 20 }, (_, i) => (i + 1) * 2),
    50,
    ...Array.from({ length: 20 }, (_, i) => (i + 1) * 3),
  ])
  return [...all].sort((a, b) => b - a)
})()

function _dartLabel(score: number): string {
  if (score === 50) return 'Bullseye'
  if (score === 25) return 'Bull'
  if (score % 3 === 0) {
    const n = score / 3
    if (n >= 1 && n <= 20) return `T${n}`
  }
  if (score % 2 === 0) {
    const n = score / 2
    if (n >= 1 && n <= 20) return `D${n}`
  }
  if (score >= 1 && score <= 20) return String(score)
  return String(score)
}

/**
 * Compute a single-out checkout suggestion (any field can finish).
 * When no finish is possible, returns a setup-shot suggestion with text "No Finish (X)".
 * Returns null only if remaining < 1.
 */
export function getSingleOutCheckout(
  remaining: number,
  dartsAvailable: number,
): CheckoutSuggestion | null {
  if (remaining < 1) return null
  const darts = Math.min(3, Math.max(1, dartsAvailable))

  // Direct 1-dart finish
  const oneLabel = _SINGLE_OUT_1DART.get(remaining)
  if (oneLabel !== undefined) {
    return { darts: [oneLabel], is_finish: true, leave: 0, text: oneLabel }
  }

  if (darts === 1) {
    // Setup shot: find dart that leaves a 1-dart finishable score
    for (const score of _ALL_SCORES_DESC) {
      const leave = remaining - score
      if (leave < 1) continue
      if (_SINGLE_OUT_1DART.has(leave)) {
        const label = _dartLabel(score)
        return { darts: [label], is_finish: false, leave, text: `No Finish (${label})` }
      }
    }
    // Fallback: reduce as much as possible
    for (const score of _ALL_SCORES_DESC) {
      const leave = remaining - score
      if (leave >= 1) {
        const label = _dartLabel(score)
        return { darts: [label], is_finish: false, leave, text: `No Finish (${label})` }
      }
    }
    return null
  }

  if (darts === 2) {
    // Try 2-dart finish
    for (const first of _ALL_SCORES_DESC) {
      const remainder = remaining - first
      if (remainder <= 0) continue
      const finLabel = _SINGLE_OUT_1DART.get(remainder)
      if (finLabel !== undefined) {
        const firstLabel = _dartLabel(first)
        const dartArr = [firstLabel, finLabel]
        return { darts: dartArr, is_finish: true, leave: 0, text: dartArr.join(' ') }
      }
    }
    // No 2-dart finish: fall back to 1-dart setup shot
    return getSingleOutCheckout(remaining, 1)
  }

  // darts === 3: try 3-dart finish (also accepts 2-dart finish)
  for (const first of _ALL_SCORES_DESC) {
    const r1 = remaining - first
    if (r1 <= 0) continue
    const fin1Label = _SINGLE_OUT_1DART.get(r1)
    if (fin1Label !== undefined) {
      const firstLabel = _dartLabel(first)
      const dartArr = [firstLabel, fin1Label]
      return { darts: dartArr, is_finish: true, leave: 0, text: dartArr.join(' ') }
    }
    for (const second of _ALL_SCORES_DESC) {
      const r2 = r1 - second
      if (r2 <= 0) continue
      const fin2Label = _SINGLE_OUT_1DART.get(r2)
      if (fin2Label !== undefined) {
        const firstLabel = _dartLabel(first)
        const secondLabel = _dartLabel(second)
        const dartArr = [firstLabel, secondLabel, fin2Label]
        return { darts: dartArr, is_finish: true, leave: 0, text: dartArr.join(' ') }
      }
    }
  }

  // No finish in ≤3 darts: fall back to 1-dart setup shot
  return getSingleOutCheckout(remaining, 1)
}
