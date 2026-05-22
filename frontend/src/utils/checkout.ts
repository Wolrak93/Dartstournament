import doubleOutTable from '../data/double_out_checkouts.json'

export interface CheckoutSuggestion {
  darts: string[]
  is_finish: boolean
  leave: number
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

  if (!pathStr || pathStr.trimStart().startsWith('No Finish') || pathStr === '') {
    return null
  }

  return {
    darts: pathStr.trim().split(/\s+/),
    is_finish: true,
    leave: 0,
  }
}
