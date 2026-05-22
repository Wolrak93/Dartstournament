import { act, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SpecialEventPopup } from '../components/SpecialEventPopup'
import type { SpecialEventItem } from '../api/types'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Total ms from start of animation until onDone fires (animation + dismiss). */
const TOTAL_MS = 1200 + 400

function makeEvent(overrides: Partial<SpecialEventItem> = {}): SpecialEventItem {
  return {
    event_type: 'tripel',
    bonus_value: 3,
    count: 1,
    ...overrides,
  }
}

/** Simple queue wrapper that simulates the parent-side queue management.
 *  Uses the same key-increment pattern as ScoreEntryScreen so each event
 *  gets a fresh component instance (displayValue resets to 0 via useState).
 */
function EventQueueWrapper({ events }: { events: SpecialEventItem[] }) {
  const [queue, setQueue] = useState(events)
  const [key, setKey] = useState(0)
  if (queue.length === 0) return <div data-testid="queue-empty">done</div>
  return (
    <SpecialEventPopup
      key={key}
      event={queue[0]}
      onDone={() => {
        setQueue((prev) => prev.slice(1))
        setKey((k) => k + 1)
      }}
    />
  )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SpecialEventPopup', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // ---- rendering ----------------------------------------------------------------

  it('renders the event name from the label map', () => {
    render(<SpecialEventPopup event={makeEvent({ event_type: '180_geworfen' })} onDone={vi.fn()} />)
    expect(screen.getByText('180!!!')).toBeInTheDocument()
  })

  it('falls back to event_type string for unknown events', () => {
    render(<SpecialEventPopup event={makeEvent({ event_type: 'unknown_event' })} onDone={vi.fn()} />)
    expect(screen.getByText('unknown_event')).toBeInTheDocument()
  })

  it('shows count suffix when count > 1', () => {
    render(<SpecialEventPopup event={makeEvent({ event_type: 'tripel', count: 3 })} onDone={vi.fn()} />)
    expect(screen.getByText(/×3/)).toBeInTheDocument()
  })

  it('does not show count suffix when count === 1', () => {
    render(<SpecialEventPopup event={makeEvent({ count: 1 })} onDone={vi.fn()} />)
    expect(screen.queryByText(/×1/)).not.toBeInTheDocument()
  })

  it('shows the ¥$ currency label for positive bonus events', () => {
    render(<SpecialEventPopup event={makeEvent({ bonus_value: 3 })} onDone={vi.fn()} />)
    expect(screen.getByText('¥$')).toBeInTheDocument()
  })

  it('shows the ¥$ currency label for negative bonus events', () => {
    render(<SpecialEventPopup event={makeEvent({ event_type: 'bogey', bonus_value: -25 })} onDone={vi.fn()} />)
    expect(screen.getByText('¥$')).toBeInTheDocument()
  })

  it('does not show ¥$ currency label when bonus_value is 0', () => {
    render(<SpecialEventPopup event={makeEvent({ bonus_value: 0 })} onDone={vi.fn()} />)
    expect(screen.queryByText('¥$')).not.toBeInTheDocument()
  })

  it('shows positive value with + prefix', () => {
    render(<SpecialEventPopup event={makeEvent({ bonus_value: 1800, event_type: '180_geworfen' })} onDone={vi.fn()} />)
    // Starts at +0 during animation
    expect(screen.getByText('+0')).toBeInTheDocument()
  })

  it('starts at 0 for negative bonus events', () => {
    render(<SpecialEventPopup event={makeEvent({ event_type: 'bogey', bonus_value: -25 })} onDone={vi.fn()} />)
    expect(screen.getByText('0')).toBeInTheDocument()
  })

  // ---- single event: animation completes and dismisses -----------------------

  it('calls onDone after animation + dismiss delay for a positive event', async () => {
    const onDone = vi.fn()
    render(<SpecialEventPopup event={makeEvent({ bonus_value: 3 })} onDone={onDone} />)

    expect(onDone).not.toHaveBeenCalled()

    await act(async () => {
      vi.advanceTimersByTime(TOTAL_MS + 50)
    })

    expect(onDone).toHaveBeenCalledTimes(1)
  })

  it('calls onDone after display period for a zero-bonus event', async () => {
    const onDone = vi.fn()
    render(<SpecialEventPopup event={makeEvent({ bonus_value: 0 })} onDone={onDone} />)

    expect(onDone).not.toHaveBeenCalled()

    await act(async () => {
      vi.advanceTimersByTime(TOTAL_MS + 50)
    })

    expect(onDone).toHaveBeenCalledTimes(1)
  })

  it('calls onDone after animation completes for a negative event', async () => {
    const onDone = vi.fn()
    render(<SpecialEventPopup event={makeEvent({ event_type: 'bogey', bonus_value: -25 })} onDone={onDone} />)

    await act(async () => {
      vi.advanceTimersByTime(TOTAL_MS + 50)
    })

    expect(onDone).toHaveBeenCalledTimes(1)
  })

  it('does not dismiss before animation finishes', async () => {
    const onDone = vi.fn()
    render(<SpecialEventPopup event={makeEvent({ bonus_value: 3 })} onDone={onDone} />)

    await act(async () => {
      vi.advanceTimersByTime(TOTAL_MS - 100)
    })

    expect(onDone).not.toHaveBeenCalled()
  })

  it('shows final value at end of animation', async () => {
    render(<SpecialEventPopup event={makeEvent({ bonus_value: 17, event_type: 'tripel_20' })} onDone={vi.fn()} />)

    await act(async () => {
      // Advance past animation but before dismiss
      vi.advanceTimersByTime(1200 + 20)
    })

    expect(screen.getByText('+17')).toBeInTheDocument()
  })

  // ---- queue: two events shown in order -------------------------------------

  it('shows the first event in a two-event queue', () => {
    const events: SpecialEventItem[] = [
      makeEvent({ event_type: 'bull', bonus_value: 25 }),
      makeEvent({ event_type: 'tripel_20', bonus_value: 17 }),
    ]
    render(<EventQueueWrapper events={events} />)

    expect(screen.getByText('Bull')).toBeInTheDocument()
    expect(screen.queryByText('Tripel 20')).not.toBeInTheDocument()
  })

  it('shows the second event after the first has dismissed', async () => {
    const events: SpecialEventItem[] = [
      makeEvent({ event_type: 'bull', bonus_value: 25 }),
      makeEvent({ event_type: 'tripel_20', bonus_value: 17 }),
    ]
    render(<EventQueueWrapper events={events} />)

    expect(screen.getByText('Bull')).toBeInTheDocument()

    // Advance past the first event's full duration
    await act(async () => {
      vi.advanceTimersByTime(TOTAL_MS + 50)
    })

    expect(screen.getByText('Tripel 20')).toBeInTheDocument()
  })

  it('renders nothing after all queued events have dismissed', async () => {
    const events: SpecialEventItem[] = [
      makeEvent({ event_type: 'bull', bonus_value: 25 }),
      makeEvent({ event_type: 'tripel_20', bonus_value: 17 }),
    ]
    render(<EventQueueWrapper events={events} />)

    // Advance past the first event, then the second in separate act() calls so that
    // timers created after the first dismissal are also processed correctly.
    await act(async () => {
      vi.advanceTimersByTime(TOTAL_MS + 50)
    })
    await act(async () => {
      vi.advanceTimersByTime(TOTAL_MS + 50)
    })

    expect(screen.getByTestId('queue-empty')).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})
