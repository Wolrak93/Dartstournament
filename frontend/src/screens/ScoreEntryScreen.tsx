import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getMatch, getMatchState, getMatchVisits, getPlayers, recordVisit, undoLastVisit } from '../api/client'
import type { MatchRead, MatchStateResponse, Player, RoundType, VisitHistoryItem, VisitResponse } from '../api/types'
import { useWebSocket } from '../hooks/useWebSocket'
import { getDoubleOutCheckout } from '../utils/checkout'
import type { CheckoutSuggestion } from '../utils/checkout'
import './ScoreEntryScreen.css'

// ---------------------------------------------------------------------------
// Single-out thresholds per round type
// ---------------------------------------------------------------------------

const SINGLE_OUT_VISIT: Record<string, number> = {
  vorrunde: 15,
  ko: 25,
  lightning: 1,
}

function roundLabel(roundType: RoundType, roundNumber: number): string {
  switch (roundType) {
    case 'vorrunde':
      return `Vorrunde — Runde ${String(roundNumber)}`
    case 'ko':
      return 'KO-Runde'
    case 'lightning':
      return 'Nebenrunde'
    default:
      return `Runde ${String(roundNumber)}`
  }
}

function formatAvg(avg: number): string {
  return avg.toFixed(2)
}

// ---------------------------------------------------------------------------
// Dart field definitions
// ---------------------------------------------------------------------------

interface DartField {
  label: string
  value: number
  band: string
  isBounce: boolean
  isRobinHood: boolean
}

const SINGLE_ROW: DartField[] = [
  { label: '0', value: 0, band: 'miss', isBounce: false, isRobinHood: false },
  ...Array.from({ length: 20 }, (_, i) => ({
    label: String(i + 1),
    value: i + 1,
    band: 'single',
    isBounce: false,
    isRobinHood: false,
  })),
  { label: 'B', value: 25, band: 'bull', isBounce: false, isRobinHood: false },
]

const DOUBLE_ROW: DartField[] = [
  { label: 'B0', value: 0, band: 'miss', isBounce: true, isRobinHood: false },
  ...Array.from({ length: 20 }, (_, i) => ({
    label: `D${i + 1}`,
    value: (i + 1) * 2,
    band: 'double',
    isBounce: false,
    isRobinHood: false,
  })),
  { label: 'BE', value: 50, band: 'bullseye', isBounce: false, isRobinHood: false },
]

const TRIPLE_ROW: DartField[] = [
  { label: 'R0', value: 0, band: 'miss', isBounce: false, isRobinHood: true },
  ...Array.from({ length: 20 }, (_, i) => ({
    label: `T${i + 1}`,
    value: (i + 1) * 3,
    band: 'triple',
    isBounce: false,
    isRobinHood: false,
  })),
]

// ---------------------------------------------------------------------------
// DartFieldSelector component
// ---------------------------------------------------------------------------

interface SelectedDart {
  field: DartField
}

interface DartFieldSelectorProps {
  onConfirm: (dart1: number, dart2: number, dart3: number, bounceFlags: boolean[], robinHoodFlags: boolean[], dartBands: string[]) => void
  onDartsChange: (total: number, count: number) => void
  disabled: boolean
}

function DartFieldSelector({ onConfirm, onDartsChange, disabled }: DartFieldSelectorProps) {
  const [darts, setDarts] = useState<(SelectedDart | null)[]>([null, null, null])
  const [activeSlot, setActiveSlot] = useState(0)

  function dartTotal(d: (SelectedDart | null)[]): number {
    return d.reduce((sum, slot) => sum + (slot?.field.value ?? 0), 0)
  }

  function selectField(field: DartField) {
    if (disabled) return
    setDarts((prev) => {
      const next = [...prev]
      next[activeSlot] = { field }
      onDartsChange(dartTotal(next), next.filter((d) => d !== null).length)
      return next
    })
    setActiveSlot((prev) => (prev < 2 ? prev + 1 : prev))
  }

  function handleSlotClick(idx: number) {
    if (disabled) return
    setActiveSlot(idx)
  }

  function handleDel() {
    if (disabled) return
    // Clear active slot; if it's empty, go back one and clear that
    setDarts((prev) => {
      const next = [...prev]
      if (next[activeSlot] !== null) {
        next[activeSlot] = null
        onDartsChange(dartTotal(next), next.filter((d) => d !== null).length)
        return next
      }
      if (activeSlot > 0) {
        next[activeSlot - 1] = null
        onDartsChange(dartTotal(next), next.filter((d) => d !== null).length)
        return next
      }
      return next
    })
    setActiveSlot((prev) => {
      if (darts[prev] !== null) return prev
      return prev > 0 ? prev - 1 : 0
    })
  }

  function handleConfirm() {
    const d1 = darts[0]?.field.value ?? 0
    const d2 = darts[1]?.field.value ?? 0
    const d3 = darts[2]?.field.value ?? 0
    const bounce = darts.map((d) => d?.field.isBounce ?? false)
    const robinHood = darts.map((d) => d?.field.isRobinHood ?? false)
    const bands = darts.map((d) => d?.field.band ?? 'miss')
    onConfirm(d1, d2, d3, bounce, robinHood, bands)
    // Reset after confirm
    setDarts([null, null, null])
    onDartsChange(0, 0)
    setActiveSlot(0)
  }

  const hasAnyDart = darts.some((d) => d !== null)

  return (
    <div className="dart-selector" aria-label="Dart-Feld-Auswahl">
      {/* Dart slots */}
      <div className="dart-slots">
        {darts.map((d, i) => (
          <button
            key={i}
            type="button"
            className={`dart-slot${i === activeSlot ? ' dart-slot--active' : ''}${d !== null ? ' dart-slot--filled' : ''}`}
            onClick={() => handleSlotClick(i)}
            disabled={disabled}
            aria-label={`Dart ${i + 1}: ${d?.field.label ?? 'leer'}`}
          >
            <span className="dart-slot-number">Dart {i + 1}</span>
            <span className="dart-slot-value">{d?.field.label ?? '—'}</span>
            {d !== null && <span className="dart-slot-pts">{d.field.value} pts</span>}
          </button>
        ))}
        <div className="dart-slots-actions">
          <button
            type="button"
            className="dart-btn dart-btn--del"
            onClick={handleDel}
            disabled={disabled || !hasAnyDart}
            aria-label="DEL"
          >
            DEL
          </button>
          <button
            type="button"
            className="dart-btn dart-btn--confirm"
            onClick={handleConfirm}
            disabled={disabled || !hasAnyDart}
          >
            ✓
          </button>
        </div>
      </div>

      {/* Field grid */}
      <div className="dart-field-grid">
        <div className="dart-field-row dart-field-row--singles">
          {SINGLE_ROW.map((f) => (
            <button
              key={f.label}
              type="button"
              className="dart-field-btn"
              onClick={() => selectField(f)}
              disabled={disabled}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="dart-field-row dart-field-row--doubles">
          {DOUBLE_ROW.map((f) => (
            <button
              key={f.label}
              type="button"
              className="dart-field-btn dart-field-btn--double"
              onClick={() => selectField(f)}
              disabled={disabled}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="dart-field-row dart-field-row--triples">
          {TRIPLE_ROW.map((f) => (
            <button
              key={f.label}
              type="button"
              className="dart-field-btn dart-field-btn--triple"
              onClick={() => selectField(f)}
              disabled={disabled}
            >
              {f.label}
            </button>
          ))}
          {/* Spacer: no triple bull exists — keeps columns aligned with single/double rows */}
          <div className="dart-field-btn dart-field-btn--spacer" aria-hidden="true" />
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main screen
// ---------------------------------------------------------------------------

export default function ScoreEntryScreen() {
  const { matchId } = useParams<{ matchId: string }>()
  const navigate = useNavigate()
  const id = matchId ? parseInt(matchId, 10) : 0

  // ---- data state ----
  const [match, setMatch] = useState<MatchRead | null>(null)
  const [matchState, setMatchState] = useState<MatchStateResponse | null>(null)
  const [playerMap, setPlayerMap] = useState<Map<number, Player>>(new Map())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // ---- visit history ----
  const [visitHistory, setVisitHistory] = useState<VisitHistoryItem[]>([])
  const [undoing, setUndoing] = useState(false)

  // ---- submission state ----
  const [submitting, setSubmitting] = useState(false)

  // ---- pending darts (entered but not yet committed) ----
  const [pendingDartTotal, setPendingDartTotal] = useState(0)
  const [pendingDartCount, setPendingDartCount] = useState(0)

  // ---- overlays ----
  const [bustActive, setBustActive] = useState(false)
  const bustTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [matchFinished, setMatchFinished] = useState(false)
  const [winnerId, setWinnerId] = useState<number | null>(null)

  // ---- websocket ----
  const { lastEvent } = useWebSocket('match', id)

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  const loadState = useCallback(() => {
    if (!id) return
    Promise.all([getMatch(id), getMatchState(id), getPlayers(), getMatchVisits(id)])
      .then(([matchData, state, playerList, visits]) => {
        setMatch(matchData)
        setMatchState(state)
        setPlayerMap(new Map(playerList.map((p) => [p.id, p])))
        setVisitHistory(visits)
        if (state.status === 'finished' && matchData.winner_id != null) {
          setMatchFinished(true)
          setWinnerId(matchData.winner_id)
        }
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Fehler beim Laden')
      })
      .finally(() => {
        setLoading(false)
      })
  }, [id])

  useEffect(() => {
    loadState()
  }, [loadState])

  // ---------------------------------------------------------------------------
  // Refresh match state
  // ---------------------------------------------------------------------------

  const refreshMatchState = useCallback(() => {
    getMatchState(id)
      .then(setMatchState)
      .catch(() => undefined)
  }, [id])

  const refreshHistory = useCallback(() => {
    getMatchVisits(id)
      .then(setVisitHistory)
      .catch(() => undefined)
  }, [id])

  // ---------------------------------------------------------------------------
  // WebSocket events
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (!lastEvent) return

    if (lastEvent.type === 'score_update') {
      const data = lastEvent.data as {
        match_finished: boolean
        winner_id: number | null
      }
      if (data.match_finished) {
        Promise.resolve({ wid: data.winner_id })
          .then(({ wid }) => {
            setMatchFinished(true)
            setWinnerId(wid)
          })
          .catch(() => undefined)
      }
      refreshMatchState()
    }

    if (lastEvent.type === 'match_finished') {
      const data = lastEvent.data as { winner_id: number | null }
      Promise.resolve(data.winner_id)
        .then((wid) => {
          setMatchFinished(true)
          setWinnerId(wid)
        })
        .catch(() => undefined)
    }

    if (lastEvent.type === 'visit_undone') {
      refreshMatchState()
      refreshHistory()
    }
  }, [lastEvent, refreshMatchState, refreshHistory])

  // Reset pending darts when the active player changes
  useEffect(() => {
    setPendingDartTotal(0)
    setPendingDartCount(0)
  }, [matchState?.current_player_id])

  // Cleanup bust timer on unmount
  useEffect(
    () => () => {
      if (bustTimerRef.current) clearTimeout(bustTimerRef.current)
    },
    [],
  )

  // ---------------------------------------------------------------------------
  // Derived values
  // ---------------------------------------------------------------------------

  const isDoubles = match?.player3_id != null

  const team1Ids: number[] = match
    ? [match.player1_id, match.player3_id].filter((x): x is number => x != null)
    : []
  const team2Ids: number[] = match
    ? [match.player2_id, match.player4_id].filter((x): x is number => x != null)
    : []

  const activePlayerId: number | null = matchState?.current_player_id ?? null

  // Single-Out threshold
  const roundType = match?.round_type ?? 'vorrunde'
  const singleOutThreshold = SINGLE_OUT_VISIT[roundType] ?? 15

  // Use the server-authoritative flag for the active player's current single-out state.
  const showSingleOutBanner = !matchFinished && matchState != null && matchState.single_out_mode

  // Per-player visit count lookup
  function visitCountForPlayer(playerId: number): number {
    if (!matchState) return 0
    if (playerId === match?.player1_id) return matchState.visit_count_p1
    if (playerId === match?.player2_id) return matchState.visit_count_p2
    if (playerId === match?.player3_id) return matchState.visit_count_p3 ?? 0
    if (playerId === match?.player4_id) return matchState.visit_count_p4 ?? 0
    return 0
  }

  // Combined visit count for an entire team (sum of all members)
  function teamVisitCount(teamIds: number[]): number {
    return teamIds.reduce((sum, pid) => sum + visitCountForPlayer(pid), 0)
  }

  // True when a team's combined visits have reached the Single-Out threshold.
  // Backend uses visit_number > threshold (strict), so done >= threshold activates SO.
  function playerSingleOutActive(playerId: number): boolean {
    if (roundType === 'lightning') return true
    const teamIds = team1Ids.includes(playerId) ? team1Ids : team2Ids
    return teamVisitCount(teamIds) >= singleOutThreshold
  }

  // Header countdown badge for the active team when single-out is not yet active
  const activeTeamIds =
    activePlayerId != null
      ? team1Ids.includes(activePlayerId)
        ? team1Ids
        : team2Ids
      : []
  const activeTeamVisitsDone =
    activePlayerId != null ? teamVisitCount(activeTeamIds) : null
  const showSingleOutCountdown =
    !matchFinished &&
    matchState != null &&
    !matchState.single_out_mode &&
    roundType !== 'lightning' &&
    activePlayerId != null

  // Dynamic checkout suggestion: recalculated as darts are entered mid-visit
  function activeDynamicCheckout(): CheckoutSuggestion | null {
    if (!matchState || activePlayerId == null || matchFinished) return null
    if (pendingDartCount === 0) {
      // No darts entered yet — use the server suggestion as-is
      return matchState.checkout_suggestion
    }
    if (matchState.single_out_mode) {
      // Single-out recalculation is not supported client-side; keep server suggestion
      return matchState.checkout_suggestion
    }
    const team1Active = team1Ids.includes(activePlayerId)
    const activeRemaining = team1Active ? matchState.remaining_p1 : matchState.remaining_p2
    const effectiveRemaining = activeRemaining - pendingDartTotal
    const dartsLeft = 3 - pendingDartCount
    return getDoubleOutCheckout(effectiveRemaining, dartsLeft)
  }

  // Per-player average lookup
  function playerAvg(playerId: number | null): number {
    if (!matchState || playerId == null) return 0
    if (playerId === match?.player1_id) return matchState.avg_p1
    if (playerId === match?.player2_id) return matchState.avg_p2
    if (playerId === match?.player3_id) return matchState.avg_p3 ?? 0
    if (playerId === match?.player4_id) return matchState.avg_p4 ?? 0
    return 0
  }

  // ---------------------------------------------------------------------------
  // Confirm handler
  // ---------------------------------------------------------------------------

  async function handleConfirm(
    dart1: number,
    dart2: number,
    dart3: number,
    bounceFlags: boolean[],
    robinHoodFlags: boolean[],
    dartBands: string[],
  ) {
    if (!matchId || !activePlayerId) return

    setSubmitting(true)

    try {
      const res: VisitResponse = await recordVisit(parseInt(matchId, 10), {
        player_id: activePlayerId,
        dart1,
        dart2,
        dart3,
        bounce_flags: bounceFlags,
        robin_hood_flags: robinHoodFlags,
        dart_bands: dartBands,
      })

      if (res.is_bust) {
        setBustActive(true)
        if (bustTimerRef.current) clearTimeout(bustTimerRef.current)
        bustTimerRef.current = setTimeout(() => setBustActive(false), 2000)
      }

      if (res.match_finished) {
        setMatchFinished(true)
        setWinnerId(res.winner_id)
      }

      const [newState, newHistory] = await Promise.all([
        getMatchState(parseInt(matchId, 10)),
        getMatchVisits(parseInt(matchId, 10)),
      ])
      setMatchState(newState)
      setVisitHistory(newHistory)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Speichern')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleUndo() {
    if (!matchId || undoing) return
    setUndoing(true)
    setError(null)
    try {
      await undoLastVisit(parseInt(matchId, 10))
      // If the match was finished, reopen it
      if (matchFinished) {
        setMatchFinished(false)
        setWinnerId(null)
      }
      const [newState, newHistory] = await Promise.all([
        getMatchState(parseInt(matchId, 10)),
        getMatchVisits(parseInt(matchId, 10)),
      ])
      setMatchState(newState)
      setVisitHistory(newHistory)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Undo fehlgeschlagen')
    } finally {
      setUndoing(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------

  function handleNextMatch() {
    navigate('/standings')
  }

  // ---------------------------------------------------------------------------
  // Render guards
  // ---------------------------------------------------------------------------

  if (loading) {
    return <div className="score-loading">Lade...</div>
  }

  if (!match || !matchState) {
    return (
      <div className="score-loading score-error-page" role="alert">
        {error ?? 'Match nicht gefunden'}
      </div>
    )
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  // Winning team: all players on the same side as winner_id
  const winnerTeamIds: number[] =
    winnerId == null
      ? []
      : team1Ids.includes(winnerId)
        ? team1Ids
        : team2Ids
  const winnerTeamNames = winnerTeamIds.map((pid) => playerMap.get(pid)?.name ?? '—').join(' & ')

  const isTeam1Active =
    activePlayerId != null && team1Ids.includes(activePlayerId)

  return (
    <div className="score-screen">
      {/* ---- header ---- */}
      <div className="score-header">
        <span className="score-round-label">{roundLabel(match.round_type, match.round_number)}</span>
        {showSingleOutBanner && (
          <span className="score-single-out-badge score-single-out-badge--active" role="alert">
            ✓ Single-Out aktiv
          </span>
        )}
        {showSingleOutCountdown && activeTeamVisitsDone != null && (
          <span className="score-single-out-badge score-single-out-badge--countdown">
            Single-Out: {activeTeamVisitsDone}&thinsp;/&thinsp;{singleOutThreshold}
          </span>
        )}
      </div>

      {/* ---- score panels ---- */}
      <div className={`score-panels${isDoubles ? ' score-panels--doubles' : ''}`}>
        {/* Team 1 */}
        <div
          className={`score-team${team1Ids.includes(activePlayerId ?? -1) ? ' score-team--active' : ''}`}
        >
          <div className="score-team-players">
            {team1Ids.map((pid) => (
              <div
                key={pid}
                className={`score-player-row${pid === activePlayerId ? ' score-player-row--active' : ''}`}
              >
                {pid === activePlayerId && <span className="score-active-arrow">{'>'}</span>}
                <span className="score-player-name">{playerMap.get(pid)?.name ?? '—'}</span>
                <span className="score-player-avg">{formatAvg(playerAvg(pid))}</span>
                {!matchFinished && (
                  <span className={`score-so-badge${playerSingleOutActive(pid) ? ' score-so-badge--active' : ''}`}>
                    {playerSingleOutActive(pid)
                      ? '✓ SO'
                      : `${teamVisitCount(team1Ids.includes(pid) ? team1Ids : team2Ids)}\u2009/\u2009${singleOutThreshold}`}
                  </span>
                )}
              </div>
            ))}
          </div>
          <div className={`score-remaining${bustActive && isTeam1Active ? ' score-remaining--bust' : ''}`}>
            {String(matchState.remaining_p1)}
            {pendingDartTotal > 0 && team1Ids.includes(activePlayerId ?? -1) && (
              <span className="score-last-visit">({matchState.remaining_p1 - pendingDartTotal})</span>
            )}
          </div>
          {isTeam1Active && !matchFinished && activeDynamicCheckout() != null && (
            <div className="score-checkout">
              {activeDynamicCheckout()!.darts.join(' ')}
            </div>
          )}
        </div>

        <div className="score-vs">VS</div>

        {/* Team 2 */}
        <div
          className={`score-team${team2Ids.includes(activePlayerId ?? -1) ? ' score-team--active' : ''}`}
        >
          <div className="score-team-players">
            {team2Ids.map((pid) => (
              <div
                key={pid}
                className={`score-player-row${pid === activePlayerId ? ' score-player-row--active' : ''}`}
              >
                {pid === activePlayerId && <span className="score-active-arrow">{'>'}</span>}
                <span className="score-player-name">{playerMap.get(pid)?.name ?? '—'}</span>
                <span className="score-player-avg">{formatAvg(playerAvg(pid))}</span>
                {!matchFinished && (
                  <span className={`score-so-badge${playerSingleOutActive(pid) ? ' score-so-badge--active' : ''}`}>
                    {playerSingleOutActive(pid)
                      ? '✓ SO'
                      : `${teamVisitCount(team1Ids.includes(pid) ? team1Ids : team2Ids)}\u2009/\u2009${singleOutThreshold}`}
                  </span>
                )}
              </div>
            ))}
          </div>
          <div className={`score-remaining${bustActive && !isTeam1Active ? ' score-remaining--bust' : ''}`}>
            {String(matchState.remaining_p2)}
            {pendingDartTotal > 0 && team2Ids.includes(activePlayerId ?? -1) && (
              <span className="score-last-visit">({matchState.remaining_p2 - pendingDartTotal})</span>
            )}
          </div>
          {!isTeam1Active && activePlayerId != null && !matchFinished && activeDynamicCheckout() != null && (
            <div className="score-checkout">
              {activeDynamicCheckout()!.darts.join(' ')}
            </div>
          )}
        </div>
      </div>

      {/* ---- error ---- */}
      {error && (
        <p className="score-inline-error" role="alert">
          {error}
        </p>
      )}

      {/* ---- dart field selector ---- */}
      {!matchFinished && (
        <DartFieldSelector
          onConfirm={(d1, d2, d3, bounce, rh, bands) => void handleConfirm(d1, d2, d3, bounce, rh, bands)}
          onDartsChange={(total, count) => {
            setPendingDartTotal(total)
            setPendingDartCount(count)
          }}
          disabled={submitting || undoing || activePlayerId == null}
        />
      )}

      {/* ---- undo button ---- */}
      {visitHistory.length > 0 && !matchFinished && (
        <div className="score-undo-bar">
          <button
            type="button"
            className="score-undo-btn"
            onClick={() => void handleUndo()}
            disabled={undoing || submitting}
            aria-label="Letzten Wurf rückgängig"
          >
            {undoing ? '...' : '↩ Letzten Wurf korrigieren'}
          </button>
        </div>
      )}

      {/* ---- bust overlay ---- */}
      {bustActive && (
        <div className="score-overlay score-overlay--bust" role="alert" aria-live="assertive">
          <div className="score-overlay-content">
            <div className="score-overlay-title">BUST!</div>
            <div className="score-overlay-sub">Score wird zurückgesetzt</div>
          </div>
        </div>
      )}

      {/* ---- match finished overlay ---- */}
      {matchFinished && (
        <div className="score-overlay score-overlay--finished" role="dialog" aria-modal="true">
          <div className="score-overlay-content">
            <div className="score-overlay-title">Spiel beendet!</div>
            {winnerTeamNames.length > 0 && (
              <div className="score-overlay-winner">
                <div className="score-overlay-winner-name">Sieger: {winnerTeamNames}</div>
              </div>
            )}
            <div className="score-overlay-scores">
              <span className="score-overlay-score-entry">
                {team1Ids.map((pid) => playerMap.get(pid)?.name ?? '—').join(' & ')}:{' '}
                {String(matchState.remaining_p1)} Rest
              </span>
              <span className="score-overlay-score-entry">
                {team2Ids.map((pid) => playerMap.get(pid)?.name ?? '—').join(' & ')}:{' '}
                {String(matchState.remaining_p2)} Rest
              </span>
            </div>
            <button
              className="score-btn score-btn--primary"
              onClick={handleNextMatch}
              type="button"
            >
              Nächstes Match
            </button>
            <button
              className="score-btn score-btn--undo"
              onClick={() => void handleUndo()}
              disabled={undoing}
              type="button"
            >
              {undoing ? '...' : '↩ Letzten Wurf korrigieren'}
            </button>
          </div>
        </div>
      )}

      {/* Placeholder hook points for Task 17 (special event popup) and Task 18 (audio) */}
    </div>
  )
}
