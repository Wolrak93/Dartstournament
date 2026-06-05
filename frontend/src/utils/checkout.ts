import doubleOutTable from '../data/double_out_checkouts.json'
import singleOutTable from '../data/single_out_checkouts.json'

export interface CheckoutSuggestion {
  darts: string[]
  is_finish: boolean
  leave: number
  text: string
}

/**
 * Look up a double-out checkout suggestion from the pre-built table.
 * Covers remaining scores 1–230 with 1, 2, or 3 darts available.
 * Returns null if no valid finish exists for the given combination.
 */
export function getDoubleOutCheckout(
  remaining: number,
  dartsAvailable: number,
): CheckoutSuggestion | null {
  if (remaining <= 0 || remaining > 230 || dartsAvailable < 1 || dartsAvailable > 3) {
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

  // "No Finish" (bare) → no valid finish or setup; display as-is
  if (trimmed === 'No Finish') {
    return { darts: [], is_finish: false, leave: -1, text: 'No Finish' }
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

/**
 * Look up a single-out checkout suggestion from the pre-built table.
 * Covers remaining scores 1–230 with 1, 2, or 3 darts available.
 * Returns null if no valid finish exists for the given combination.
 */
export function getSingleOutCheckout(
  remaining: number,
  dartsAvailable: number,
): CheckoutSuggestion | null {
  if (remaining <= 0 || remaining > 230 || dartsAvailable < 1 || dartsAvailable > 3) {
    return null
  }

  const entry = (singleOutTable as string[][])[remaining]
  if (!entry) return null

  // Table layout per entry: [3-dart path, 2-dart path, 1-dart path, score]
  const pathStr = entry[3 - dartsAvailable]

  if (!pathStr || pathStr === '') {
    return null
  }

  const trimmed = pathStr.trim()

  // "No Finish" (bare) → no valid finish or setup; display as-is
  if (trimmed === 'No Finish') {
    return { darts: [], is_finish: false, leave: -1, text: 'No Finish' }
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
