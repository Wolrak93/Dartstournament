import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getMatch, getMatchState, getPlayers, recordVisit } from '../api/client'
import type { MatchRead, MatchStateResponse, Player, RoundType, VisitResponse } from '../api/types'
import { useWebSocket } from '../hooks/useWebSocket'
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
  isBounce: boolean
  isRobinHood: boolean
}

const SINGLE_ROW: DartField[] = [
  { label: '0', value: 0, isBounce: false, isRobinHood: false },
  ...Array.from({ length: 20 }, (_, i) => ({
    label: String(i + 1),
    value: i + 1,
    isBounce: false,
    isRobinHood: false,
  })),
  { label: 'B', value: 25, isBounce: false, isRobinHood: false },
]

const DOUBLE_ROW: DartField[] = [
  { label: 'B0', value: 0, isBounce: true, isRobinHood: false },
  ...Array.from({ length: 20 }, (_, i) => ({
    label: `D${i + 1}`,
    value: (i + 1) * 2,
    isBounce: false,
    isRobinHood: false,
  })),
  { label: 'BE', value: 50, isBounce: false, isRobinHood: false },
]

const TRIPLE_ROW: DartField[] = [
  { label: 'R0', value: 0, isBounce: false, isRobinHood: true },
  ...Array.from({ length: 20 }, (_, i) => ({
    label: `T${i + 1}`,
    value: (i + 1) * 3,
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
  onConfirm: (dart1: number, dart2: number, dart3: number, bounceFlags: boolean[], robinHoodFlags: boolean[]) => void
  disabled: boolean
}

function DartFieldSelector({ onConfirm, disabled }: DartFieldSelectorProps) {
  const [darts, setDarts] = useState<(SelectedDart | null)[]>([null, null, null])
  const [activeSlot, setActiveSlot] = useState(0)

  function selectField(field: DartField) {
    if (disabled) return
    setDarts((prev) => {
      const next = [...prev]
      next[activeSlot] = { field }
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
        return next
      }
      if (activeSlot > 0) {
        next[activeSlot - 1] = null
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
    onConfirm(d1, d2, d3, bounce, robinHood)
    // Reset after confirm
    setDarts([null, null, null])
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

  // ---- doubles: manually chosen active player ----
  const [doublesActivePlayer, setDoublesActivePlayer] = useState<number | null>(null)

  // ---- submission state ----
  const [submitting, setSubmitting] = useState(false)

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
    Promise.all([getMatch(id), getMatchState(id), getPlayers()])
      .then(([matchData, state, playerList]) => {
        setMatch(matchData)
        setMatchState(state)
        setPlayerMap(new Map(playerList.map((p) => [p.id, p])))
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
  }, [lastEvent, refreshMatchState])

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

  const activePlayerId: number | null = isDoubles
    ? doublesActivePlayer
    : (matchState?.current_player_id ?? null)

  // Single-Out threshold
  const roundType = match?.round_type ?? 'vorrunde'
  const singleOutThreshold = SINGLE_OUT_VISIT[roundType] ?? 15
  const currentVisitCount = matchState
    ? activePlayerId != null && team1Ids.includes(activePlayerId)
      ? matchState.visit_count_p1
      : matchState.visit_count_p2
    : 0
  const showSingleOutBanner =
    !matchFinished && matchState != null && currentVisitCount >= singleOutThreshold

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

      const newState = await getMatchState(parseInt(matchId, 10))
      setMatchState(newState)

      if (isDoubles) {
        setDoublesActivePlayer(null)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Speichern')
    } finally {
      setSubmitting(false)
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

  const winnerPlayer = winnerId != null ? playerMap.get(winnerId) : null
  const isTeam1Active =
    activePlayerId != null && team1Ids.includes(activePlayerId)

  return (
    <div className="score-screen">
      {/* ---- header ---- */}
      <div className="score-header">
        <span className="score-round-label">{roundLabel(match.round_type, match.round_number)}</span>
        {showSingleOutBanner && (
          <span className="score-single-out-badge" role="alert">
            Single-Out aktiv
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
                onClick={
                  isDoubles && !matchFinished
                    ? () => {
                        setDoublesActivePlayer(pid)
                      }
                    : undefined
                }
                role={isDoubles && !matchFinished ? 'button' : undefined}
                tabIndex={isDoubles && !matchFinished ? 0 : undefined}
                onKeyDown={
                  isDoubles && !matchFinished
                    ? (e) => {
                        if (e.key === 'Enter' || e.key === ' ') setDoublesActivePlayer(pid)
                      }
                    : undefined
                }
                aria-label={
                  isDoubles && !matchFinished
                    ? `${playerMap.get(pid)?.name ?? '?'} auswählen`
                    : undefined
                }
              >
                {pid === activePlayerId && <span className="score-active-arrow">{'>'}</span>}
                <span className="score-player-name">{playerMap.get(pid)?.name ?? '—'}</span>
                <span className="score-player-avg">{formatAvg(playerAvg(pid))}</span>
              </div>
            ))}
          </div>
          <div className={`score-remaining${bustActive && isTeam1Active ? ' score-remaining--bust' : ''}`}>
            {String(matchState.remaining_p1)}
            {matchState.last_visit_total != null && team1Ids.includes(activePlayerId ?? -1) && (
              <span className="score-last-visit">({matchState.last_visit_total})</span>
            )}
          </div>
          {matchState.checkout_suggestion != null && isTeam1Active && !matchFinished && (
            <div className="score-checkout">
              {matchState.checkout_suggestion.darts.join(' ')}
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
                onClick={
                  isDoubles && !matchFinished
                    ? () => {
                        setDoublesActivePlayer(pid)
                      }
                    : undefined
                }
                role={isDoubles && !matchFinished ? 'button' : undefined}
                tabIndex={isDoubles && !matchFinished ? 0 : undefined}
                onKeyDown={
                  isDoubles && !matchFinished
                    ? (e) => {
                        if (e.key === 'Enter' || e.key === ' ') setDoublesActivePlayer(pid)
                      }
                    : undefined
                }
                aria-label={
                  isDoubles && !matchFinished
                    ? `${playerMap.get(pid)?.name ?? '?'} auswählen`
                    : undefined
                }
              >
                {pid === activePlayerId && <span className="score-active-arrow">{'>'}</span>}
                <span className="score-player-name">{playerMap.get(pid)?.name ?? '—'}</span>
                <span className="score-player-avg">{formatAvg(playerAvg(pid))}</span>
              </div>
            ))}
          </div>
          <div className={`score-remaining${bustActive && !isTeam1Active ? ' score-remaining--bust' : ''}`}>
            {String(matchState.remaining_p2)}
            {matchState.last_visit_total != null && team2Ids.includes(activePlayerId ?? -1) && (
              <span className="score-last-visit">({matchState.last_visit_total})</span>
            )}
          </div>
          {matchState.checkout_suggestion != null && !isTeam1Active && activePlayerId != null && !matchFinished && (
            <div className="score-checkout">
              {matchState.checkout_suggestion.darts.join(' ')}
            </div>
          )}
        </div>
      </div>

      {/* ---- doubles hint ---- */}
      {isDoubles && !matchFinished && doublesActivePlayer == null && (
        <p className="score-doubles-hint" role="status">
          Spieler antippen, der wirft
        </p>
      )}

      {/* ---- error ---- */}
      {error && (
        <p className="score-inline-error" role="alert">
          {error}
        </p>
      )}

      {/* ---- dart field selector ---- */}
      {!matchFinished && (
        <DartFieldSelector
          onConfirm={(d1, d2, d3, bounce, rh) => void handleConfirm(d1, d2, d3, bounce, rh)}
          disabled={submitting || activePlayerId == null}
        />
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
            {winnerPlayer != null && (
              <div className="score-overlay-winner">
                <div className="score-overlay-winner-name">Sieger: {winnerPlayer.name}</div>
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
          </div>
        </div>
      )}

      {/* Placeholder hook points for Task 17 (special event popup) and Task 18 (audio) */}
    </div>
  )
}
