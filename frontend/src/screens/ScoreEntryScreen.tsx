import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getMatch, getMatchState, getPlayers, playerPhotoUrl, recordVisit } from '../api/client'
import type { MatchRead, MatchStateResponse, Player, RoundType, VisitResponse } from '../api/types'
import { useWebSocket } from '../hooks/useWebSocket'
import { splitTotal } from '../utils/dartUtils'
import './ScoreEntryScreen.css'

// ---------------------------------------------------------------------------
// Single-out thresholds per round type
// ---------------------------------------------------------------------------

const SINGLE_OUT_VISIT: Record<string, number> = {
  vorrunde: 15,
  ko: 25,
  lightning: 1, // always single-out from visit 1
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

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface PlayerPanelProps {
  player: Player | undefined
  remaining: number
  visitCount: number
  isActive: boolean
  isBust: boolean
}

function PlayerPanel({ player, remaining, visitCount, isActive, isBust }: PlayerPanelProps) {
  return (
    <div
      className={`score-player-panel${isActive ? ' score-player-panel--active' : ''}${isBust ? ' score-player-panel--bust' : ''}`}
      aria-current={isActive ? 'true' : undefined}
    >
      <div className="score-player-photo">
        {player?.photo_path ? (
          <img src={playerPhotoUrl(player.photo_path)} alt={player?.name ?? ''} />
        ) : (
          <div className="score-player-photo-placeholder" />
        )}
      </div>
      <div className="score-player-name">{player?.name ?? '—'}</div>
      <div className="score-remaining" aria-label={`Verbleibend: ${String(remaining)}`}>
        {String(remaining)}
      </div>
      <div className="score-visit-count">Besuche: {String(visitCount)}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Numpad
// ---------------------------------------------------------------------------

interface NumpadProps {
  value: string
  onDigit: (d: string) => void
  onDelete: () => void
  onConfirm: () => void
  disabled: boolean
}

function Numpad({ value, onDigit, onDelete, onConfirm, disabled }: NumpadProps) {
  return (
    <div className="score-numpad" aria-label="Numpad">
      <div className="score-input-display" aria-live="polite">
        {value === '' ? <span className="score-input-placeholder">—</span> : value}
      </div>
      <div className="score-numpad-grid">
        {['7', '8', '9', '4', '5', '6', '1', '2', '3'].map((d) => (
          <button
            key={d}
            className="score-numpad-btn score-numpad-btn--digit"
            onClick={() => onDigit(d)}
            disabled={disabled}
            type="button"
          >
            {d}
          </button>
        ))}
        <button
          className="score-numpad-btn score-numpad-btn--del"
          onClick={onDelete}
          disabled={disabled}
          type="button"
        >
          DEL
        </button>
        <button
          className="score-numpad-btn score-numpad-btn--digit"
          onClick={() => onDigit('0')}
          disabled={disabled}
          type="button"
        >
          0
        </button>
        <button
          className="score-numpad-btn score-numpad-btn--confirm"
          onClick={onConfirm}
          disabled={disabled || value === ''}
          type="button"
        >
          ✓
        </button>
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

  // ---- numpad ----
  const [inputValue, setInputValue] = useState('')
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
  // Refresh match state (used after visits and WebSocket events)
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
        // Wrap in .then() to avoid direct setState in effect body
        Promise.resolve({ finished: true, wid: data.winner_id })
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
  useEffect(() => () => {
    if (bustTimerRef.current) clearTimeout(bustTimerRef.current)
  }, [])

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

  // Active player for score entry
  const activePlayerId: number | null = isDoubles
    ? doublesActivePlayer
    : (matchState?.current_player_id ?? null)

  // Remaining for current active player's team
  function remainingForPlayer(playerId: number | null): number {
    if (!matchState || !match || playerId == null) return 0
    return team1Ids.includes(playerId) ? matchState.remaining_p1 : matchState.remaining_p2
  }

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

  // ---------------------------------------------------------------------------
  // Numpad handlers
  // ---------------------------------------------------------------------------

  function handleDigit(d: string) {
    setInputValue((prev) => {
      if (prev.length >= 3) return prev
      const next = prev + d
      if (parseInt(next, 10) > 180) return prev
      return next
    })
  }

  function handleDelete() {
    setInputValue((prev) => prev.slice(0, -1))
  }

  async function handleConfirm() {
    if (!matchId || !activePlayerId || inputValue === '') return
    const total = parseInt(inputValue, 10)
    if (isNaN(total) || total < 0 || total > 180) return

    setSubmitting(true)
    setInputValue('')

    const [d1, d2, d3] = splitTotal(total)
    try {
      const res: VisitResponse = await recordVisit(parseInt(matchId, 10), {
        player_id: activePlayerId,
        dart1: d1,
        dart2: d2,
        dart3: d3,
        bounce_flags: [false, false, false],
        robin_hood_flags: [false, false, false],
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

  return (
    <div className="score-screen">
      {/* ---- header ---- */}
      <div className="score-header">
        <span className="score-round-label">{roundLabel(match.round_type, match.round_number)}</span>
        {matchState.single_out_mode && !showSingleOutBanner && (
          <span className="score-single-out-badge">Single-Out</span>
        )}
      </div>

      {/* ---- single-out warning banner ---- */}
      {showSingleOutBanner && (
        <div className="score-single-out-banner" role="alert">
          ⚠ Single-Out aktiv
        </div>
      )}

      {/* ---- score panels ---- */}
      <div className={`score-panels${isDoubles ? ' score-panels--doubles' : ''}`}>
        {/* Team 1 */}
        <div className="score-team">
          {team1Ids.map((pid) => (
            <div
              key={pid}
              className={isDoubles ? 'score-doubles-player-wrapper' : ''}
              onClick={
                isDoubles && !matchFinished
                  ? () => {
                      setDoublesActivePlayer(pid)
                      setInputValue('')
                    }
                  : undefined
              }
              role={isDoubles && !matchFinished ? 'button' : undefined}
              tabIndex={isDoubles && !matchFinished ? 0 : undefined}
              onKeyDown={
                isDoubles && !matchFinished
                  ? (e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        setDoublesActivePlayer(pid)
                        setInputValue('')
                      }
                    }
                  : undefined
              }
              aria-label={
                isDoubles && !matchFinished
                  ? `${playerMap.get(pid)?.name ?? '?'} auswählen`
                  : undefined
              }
            >
              <PlayerPanel
                player={playerMap.get(pid)}
                remaining={matchState.remaining_p1}
                visitCount={matchState.visit_count_p1}
                isActive={pid === activePlayerId}
                isBust={bustActive && pid === activePlayerId}
              />
            </div>
          ))}
        </div>

        <div className="score-vs">VS</div>

        {/* Team 2 */}
        <div className="score-team">
          {team2Ids.map((pid) => (
            <div
              key={pid}
              className={isDoubles ? 'score-doubles-player-wrapper' : ''}
              onClick={
                isDoubles && !matchFinished
                  ? () => {
                      setDoublesActivePlayer(pid)
                      setInputValue('')
                    }
                  : undefined
              }
              role={isDoubles && !matchFinished ? 'button' : undefined}
              tabIndex={isDoubles && !matchFinished ? 0 : undefined}
              onKeyDown={
                isDoubles && !matchFinished
                  ? (e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        setDoublesActivePlayer(pid)
                        setInputValue('')
                      }
                    }
                  : undefined
              }
              aria-label={
                isDoubles && !matchFinished
                  ? `${playerMap.get(pid)?.name ?? '?'} auswählen`
                  : undefined
              }
            >
              <PlayerPanel
                player={playerMap.get(pid)}
                remaining={matchState.remaining_p2}
                visitCount={matchState.visit_count_p2}
                isActive={pid === activePlayerId}
                isBust={bustActive && pid === activePlayerId}
              />
            </div>
          ))}
        </div>
      </div>

      {/* ---- doubles hint ---- */}
      {isDoubles && !matchFinished && doublesActivePlayer == null && (
        <p className="score-doubles-hint" role="status">
          Bitte Spieler antippen, der wirft
        </p>
      )}

      {/* ---- active player indicator (singles) ---- */}
      {!isDoubles && activePlayerId != null && !matchFinished && (
        <div className="score-active-indicator" aria-live="polite">
          Am Zug: <strong>{playerMap.get(activePlayerId)?.name ?? '—'}</strong>
        </div>
      )}

      {/* ---- checkout suggestion ---- */}
      {matchState.checkout_suggestion != null &&
        remainingForPlayer(activePlayerId) <= 170 &&
        !matchFinished && (
          <div className="score-checkout" aria-live="polite">
            <span className="score-checkout-label">Checkout:</span>
            {matchState.checkout_suggestion.darts.join(' → ')}
            {matchState.checkout_suggestion.is_finish && (
              <span className="score-checkout-finish"> (Finish!)</span>
            )}
          </div>
        )}

      {/* ---- error ---- */}
      {error && (
        <p className="score-inline-error" role="alert">
          {error}
        </p>
      )}

      {/* ---- numpad ---- */}
      {!matchFinished && (
        <Numpad
          value={inputValue}
          onDigit={handleDigit}
          onDelete={handleDelete}
          onConfirm={() => void handleConfirm()}
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
                {winnerPlayer.photo_path && (
                  <img
                    className="score-overlay-photo"
                    src={playerPhotoUrl(winnerPlayer.photo_path)}
                    alt={winnerPlayer.name}
                  />
                )}
                <div className="score-overlay-winner-name">Sieger: {winnerPlayer.name}</div>
              </div>
            )}
            <div className="score-overlay-scores">
              {team1Ids.map((pid) => {
                const p = playerMap.get(pid)
                return (
                  <span key={pid} className="score-overlay-score-entry">
                    {p?.name ?? '—'}: {String(matchState.remaining_p1)} Rest
                  </span>
                )
              })}
              {team2Ids.map((pid) => {
                const p = playerMap.get(pid)
                return (
                  <span key={pid} className="score-overlay-score-entry">
                    {p?.name ?? '—'}: {String(matchState.remaining_p2)} Rest
                  </span>
                )
              })}
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
      {/* These will be wired up when the respective tasks are implemented. */}
    </div>
  )
}
