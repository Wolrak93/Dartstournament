import { useEffect, useRef, useState } from 'react'
import type { SpecialEventItem } from '../api/types'
import './SpecialEventPopup.css'

// ---------------------------------------------------------------------------
// Event label mapping (event_type → display name)
// ---------------------------------------------------------------------------

const EVENT_LABELS: Record<string, string> = {
  '26_geworfen': '26 geworfen',
  '180_geworfen': '180!!!',
  '170_rest': '170 Rest',
  kack_rest: 'Kack-Rest',
  bogey: 'Bogey',
  tripel: 'Tripel',
  tripel_20: 'Tripel 20',
  bull: 'Bull',
  bullseye: 'Bulls Eye',
  bounce: 'Bounce',
  robin_hood: 'Robin Hood',
  be_finish: 'BE Finish',
  odd_finish: 'Odd Finish',
  double_double: 'Double Double',
  mad_house: 'Mad House',
  shanghai: 'Shanghai!',
  bust: 'BUST',
  doppel_treffer: 'Doppel-Treffer',
  gleiche_zahl: 'Gleiche Zahl',
}

// ---------------------------------------------------------------------------
// Timing constants
// ---------------------------------------------------------------------------

const ANIMATION_DURATION_MS = 1200
const DISMISS_DELAY_MS = 400
/** Interval tick rate (~25 fps). Must be kept in sync with test expectations. */
const TICK_MS = 40

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface SpecialEventPopupProps {
  event: SpecialEventItem
  onDone: () => void
}

export function SpecialEventPopup({ event, onDone }: SpecialEventPopupProps) {
  const startValue = event.tournament_count - event.count
  const [displayValue, setDisplayValue] = useState(startValue)

  // Always hold the latest onDone without re-triggering the animation effect
  const onDoneRef = useRef(onDone)
  useEffect(() => {
    onDoneRef.current = onDone
  })

  useEffect(() => {
    // Note: the parent mounts a fresh component instance via a key prop for each
    // new event, so displayValue always starts at startValue — no reset needed here.

    const start = event.tournament_count - event.count
    const target = event.tournament_count
    const startTime = Date.now()

    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime

      // Animate counter until ANIMATION_DURATION_MS, then hold for DISMISS_DELAY_MS
      if (elapsed < ANIMATION_DURATION_MS) {
        const progress = elapsed / ANIMATION_DURATION_MS
        // Ease-out cubic: slow down near the end for dramatic effect
        const eased = 1 - Math.pow(1 - progress, 3)
        setDisplayValue(Math.round(start + eased * (target - start)))
      } else {
        setDisplayValue(target)
      }

      if (elapsed >= ANIMATION_DURATION_MS + DISMISS_DELAY_MS) {
        clearInterval(interval)
        onDoneRef.current()
      }
    }, TICK_MS)

    return () => clearInterval(interval)
  }, [event]) // Re-run only when a new event arrives

  const isPositive = event.bonus_value > 0
  const isNegative = event.bonus_value < 0

  const label = EVENT_LABELS[event.event_type] ?? event.event_type
  const countSuffix = event.count > 1 ? ` ×${event.count}` : ''

  return (
    <div className="event-popup" role="status" aria-live="assertive">
      <div
        className={[
          'event-popup-card',
          isPositive
            ? 'event-popup-card--positive'
            : isNegative
              ? 'event-popup-card--negative'
              : 'event-popup-card--neutral',
        ].join(' ')}
      >
        <div className="event-popup-name">
          {label}
          {countSuffix}
        </div>

        <div
          className={`event-popup-value ${isPositive ? 'event-popup-value--positive' : isNegative ? 'event-popup-value--negative' : ''}`}
        >
          {displayValue}
        </div>
      </div>
    </div>
  )
}
