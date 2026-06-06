/**
 * Distribute a visit total (0–180) across up to 3 darts (each 0–60).
 * Used when the referee enters a total score rather than individual dart scores.
 */
export function splitTotal(total: number): [number, number, number] {
  const d1 = Math.min(total, 60)
  const d2 = Math.min(total - d1, 60)
  const d3 = total - d1 - d2
  return [d1, d2, d3]
}
