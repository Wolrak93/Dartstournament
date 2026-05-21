import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getMatch,
  getPlayers,
  playerPhotoUrl,
  recordBullThrow,
  startMatch,
} from '../api/client'
import type { BullThrowResponse, MatchRead, Player, RoundType } from '../api/types'
import './BullThrowScreen.css'

type Phase = 'select' | 'tie' | 'result'

// In doubles mode, selection happens in two sub-steps:
//   step 1 — pick the overall best thrower (any of 4 players)
//   step 2 — pick the best thrower from the opposing team
type DoublesStep = 1 | 2

export default function BullThrowScreen() {
  const { matchId } = useParams<{ matchId: string }>()
  const navigate = useNavigate()

  const [match, setMatch] = useState<MatchRead | null>(null)
  const [playerMap, setPlayerMap] = useState<Map<number, Player>>(new Map())
  const [phase, setPhase] = useState<Phase>('select')
  const [result, setResult] = useState<BullThrowResponse | null>(null)

  // Singles: selectedWinner holds winner_id
  // Doubles step 1: selectedWinner holds best_player_id
  // Doubles step 2: selectedOpponent holds best_opponent_id
  const [selectedWinner, setSelectedWinner] = useState<number | null>(null)
  const [selectedOpponent, setSelectedOpponent] = useState<number | null>(null)
  const [doublesStep, setDoublesStep] = useState<DoublesStep>(1)

  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!matchId) return
    const id = parseInt(matchId, 10)
    Promise.all([getMatch(id), getPlayers()])
      .then(([matchData, playerList]) => {
        setMatch(matchData)
        setPlayerMap(new Map(playerList.map((p) => [p.id, p])))
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Fehler beim Laden')
      })
      .finally(() => {
        setLoading(false)
      })
  }, [matchId])

  if (loading) {
    return <div className="bull-loading">Lade...</div>
  }

  if (!match) {
    return (
      <div className="bull-loading bull-error-page" role="alert">
        {error ?? 'Match nicht gefunden'}
      </div>
    )
  }

  const isDoubles = match.player3_id != null

  const team1: number[] = [match.player1_id, match.player3_id].filter(
    (id): id is number => id != null,
  )
  const team2: number[] = [match.player2_id, match.player4_id].filter(
    (id): id is number => id != null,
  )

  // ---------------------------------------------------------------------------
  // Click handlers
  // ---------------------------------------------------------------------------

  function handleTie() {
    setSelectedWinner(null)
    setSelectedOpponent(null)
    setDoublesStep(1)
    setPhase('tie')
  }

  function resetSelection() {
    setSelectedWinner(null)
    setSelectedOpponent(null)
    setDoublesStep(1)
    setPhase('select')
  }

  function handleSinglesClick(playerId: number) {
    setSelectedWinner(playerId)
    setError(null)
  }

  function handleDoublesClick(playerId: number) {
    setError(null)
    if (doublesStep === 1) {
      setSelectedWinner(playerId)
      setSelectedOpponent(null)
      setDoublesStep(2)
    } else {
      // Step 2: only allow click on opposing team
      const winnerTeam = selectedWinner !== null && team1.includes(selectedWinner) ? team1 : team2
      if (winnerTeam.includes(playerId)) {
        // Clicked same team — restart from step 1
        setSelectedWinner(playerId)
        setSelectedOpponent(null)
        setDoublesStep(2)
      } else {
        setSelectedOpponent(playerId)
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------

  function handleSubmit() {
    if (!matchId) return
    setError(null)

    if (!isDoubles) {
      if (!selectedWinner) {
        setError('Bitte einen Spieler auswählen.')
        return
      }
      void doSubmitSingles(selectedWinner)
    } else {
      if (!selectedWinner || !selectedOpponent) {
        setError('Bitte beide Spieler auswählen.')
        return
      }
      void doSubmitDoubles(selectedWinner, selectedOpponent)
    }
  }

  async function doSubmitSingles(winnerId: number) {
    if (!matchId) return
    setSubmitting(true)
    try {
      const res = await recordBullThrow(parseInt(matchId, 10), { winner_id: winnerId })
      setResult(res)
      setPhase('result')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Bull Throw')
    } finally {
      setSubmitting(false)
    }
  }

  async function doSubmitDoubles(bestPlayerId: number, bestOpponentId: number) {
    if (!matchId) return
    setSubmitting(true)
    try {
      const res = await recordBullThrow(parseInt(matchId, 10), {
        best_player_id: bestPlayerId,
        best_opponent_id: bestOpponentId,
      })
      setResult(res)
      setPhase('result')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Bull Throw')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleContinue() {
    if (!match || !matchId) return
    try {
      await startMatch(parseInt(matchId, 10))
    } catch {
      // If match is already started, proceed anyway
    }
    // Walk-on screen (Task 19) will be inserted here for KO/Lightning once implemented.
    navigate(`/score/${matchId}`)
  }

  // ---------------------------------------------------------------------------
  // Derived UI helpers
  // ---------------------------------------------------------------------------

  const startingPlayer = result ? playerMap.get(result.starting_player_id) : null

  // Instruction text
  let instruction: string
  if (phase === 'tie') {
    instruction = 'Unentschieden — bitte erneut werfen'
  } else if (!isDoubles) {
    instruction = 'Wer hat näher an der Bull geworfen?'
  } else if (doublesStep === 1) {
    instruction = 'Schritt 1: Wer hat am nächsten geworfen? (beliebiger Spieler)'
  } else {
    instruction = 'Schritt 2: Wer vom anderen Team hat am nächsten geworfen?'
  }

  // Whether the submit button should be enabled
  const canSubmit = isDoubles
    ? selectedWinner !== null && selectedOpponent !== null
    : selectedWinner !== null

  // For doubles step 2: which players are still selectable (opposing team only)
  function isSelectable(playerId: number): boolean {
    if (!isDoubles) return true
    if (doublesStep === 1) return true
    const winnerTeam = selectedWinner !== null && team1.includes(selectedWinner) ? team1 : team2
    return !winnerTeam.includes(playerId)
  }

  function cardState(playerId: number): 'selected-winner' | 'selected-opponent' | 'disabled' | 'default' {
    if (playerId === selectedWinner) return 'selected-winner'
    if (playerId === selectedOpponent) return 'selected-opponent'
    if (isDoubles && doublesStep === 2 && !isSelectable(playerId)) return 'disabled'
    return 'default'
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="bull-screen">
      <h1 className="bull-title">Bull Throw</h1>
      <p className="bull-round">{roundLabel(match.round_type, match.round_number)}</p>

      {phase !== 'result' && (
        <>
          <p
            className={`bull-instruction${phase === 'tie' ? ' bull-instruction--tie' : ''}`}
            role={phase === 'tie' ? 'alert' : undefined}
          >
            {instruction}
          </p>

          <div className={`bull-players${isDoubles ? ' bull-players--doubles' : ''}`}>
            <div className="bull-team">
              {team1.map((pid) => {
                const state = cardState(pid)
                const clickable = state !== 'disabled'
                return (
                  <SelectableCard
                    key={pid}
                    player={playerMap.get(pid)}
                    state={state}
                    onClick={
                      clickable
                        ? () =>
                            isDoubles ? handleDoublesClick(pid) : handleSinglesClick(pid)
                        : undefined
                    }
                  />
                )
              })}
            </div>
            <div className="bull-vs">VS</div>
            <div className="bull-team">
              {team2.map((pid) => {
                const state = cardState(pid)
                const clickable = state !== 'disabled'
                return (
                  <SelectableCard
                    key={pid}
                    player={playerMap.get(pid)}
                    state={state}
                    onClick={
                      clickable
                        ? () =>
                            isDoubles ? handleDoublesClick(pid) : handleSinglesClick(pid)
                        : undefined
                    }
                  />
                )
              })}
            </div>
          </div>

          {error && (
            <p className="bull-inline-error" role="alert">
              {error}
            </p>
          )}

          <div className="bull-actions">
            <button
              className="bull-btn bull-btn--secondary"
              onClick={phase === 'tie' ? resetSelection : handleTie}
            >
              {phase === 'tie' ? 'Neu auswählen' : 'Unentschieden'}
            </button>
            <button
              className="bull-btn bull-btn--primary"
              onClick={handleSubmit}
              disabled={!canSubmit || submitting}
            >
              Auswerten
            </button>
          </div>
        </>
      )}

      {phase === 'result' && result && (
        <div className="bull-result">
          <div className="bull-result-banner">
            {startingPlayer
              ? `${startingPlayer.name} wirft zuerst!`
              : `Spieler ${String(result.starting_player_id)} wirft zuerst!`}
          </div>
          <div className={`bull-players${isDoubles ? ' bull-players--doubles' : ''}`}>
            <div className="bull-team">
              {team1.map((pid) => (
                <PlayerCard
                  key={pid}
                  player={playerMap.get(pid)}
                  isStarter={result.play_order[0] === pid}
                />
              ))}
            </div>
            <div className="bull-vs">VS</div>
            <div className="bull-team">
              {team2.map((pid) => (
                <PlayerCard
                  key={pid}
                  player={playerMap.get(pid)}
                  isStarter={result.play_order[0] === pid}
                />
              ))}
            </div>
          </div>
          <button className="bull-btn bull-btn--primary" onClick={() => void handleContinue()}>
            Weiter
          </button>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

type CardState = 'selected-winner' | 'selected-opponent' | 'disabled' | 'default'

interface SelectableCardProps {
  player: Player | undefined
  state: CardState
  onClick?: () => void
}

function SelectableCard({ player, state, onClick }: SelectableCardProps) {
  return (
    <button
      className={`bull-player-card bull-player-card--${state}`}
      onClick={onClick}
      disabled={state === 'disabled'}
      type="button"
    >
      <PlayerPhoto player={player} />
      <div className="bull-player-name">{player?.name ?? '—'}</div>
      {state === 'selected-winner' && <div className="bull-selection-badge bull-selection-badge--winner">✓ Bester</div>}
      {state === 'selected-opponent' && <div className="bull-selection-badge bull-selection-badge--opponent">✓ Bester Gegner</div>}
    </button>
  )
}

interface PlayerCardProps {
  player: Player | undefined
  isStarter: boolean
}

function PlayerCard({ player, isStarter }: PlayerCardProps) {
  return (
    <div className={`bull-player-card bull-player-card--${isStarter ? 'selected-winner' : 'default'}`}>
      <PlayerPhoto player={player} />
      <div className="bull-player-name">{player?.name ?? '—'}</div>
      {isStarter && <div className="bull-selection-badge bull-selection-badge--winner">Wirft zuerst</div>}
    </div>
  )
}

function PlayerPhoto({ player }: { player: Player | undefined }) {
  return (
    <div className="bull-player-photo">
      {player?.photo_path ? (
        <img src={playerPhotoUrl(player.photo_path)} alt={player.name} />
      ) : (
        <div className="bull-player-photo-placeholder" />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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
