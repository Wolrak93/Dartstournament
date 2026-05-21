import { useEffect, useState, useCallback } from 'react'
import { useTournament } from '../contexts/TournamentContext'
import { useWebSocket } from '../hooks/useWebSocket'
import { getLightning, getPlayers } from '../api/client'
import type { LightningMatchRead, Player } from '../api/types'
import NavBar from '../components/NavBar'
import './overview.css'
import './LightningScreen.css'

const STATUS_LABELS: Record<string, string> = {
  pending: 'Ausstehend',
  bull_throw: 'Bull-Throw',
  in_progress: 'Läuft',
  finished: 'Beendet',
}

function playerName(id: number, map: Record<number, Player>): string {
  return map[id]?.name ?? `#${id}`
}

export default function LightningScreen() {
  const { tournamentId } = useTournament()
  const [matches, setMatches] = useState<LightningMatchRead[]>([])
  const [playerMap, setPlayerMap] = useState<Record<number, Player>>({})
  const [error, setError] = useState<string | null>(null)
  const [noLightning, setNoLightning] = useState(false)

  useEffect(() => {
    getPlayers()
      .then(players => {
        const map: Record<number, Player> = {}
        players.forEach(p => {
          map[p.id] = p
        })
        setPlayerMap(map)
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Fehler beim Laden'))
  }, [])

  const loadLightning = useCallback(() => {
    if (tournamentId === null) return
    getLightning(tournamentId)
      .then(data => {
        setMatches(data.matches)
        setNoLightning(data.matches.length === 0)
      })
      .catch(() => {
        setNoLightning(true)
      })
  }, [tournamentId])

  useEffect(() => {
    loadLightning()
  }, [loadLightning])

  const { lastEvent } = useWebSocket('tournament', tournamentId ?? 0)

  useEffect(() => {
    if (lastEvent?.type === 'bracket_update' || lastEvent?.type === 'standings_update') {
      loadLightning()
    }
  }, [lastEvent, loadLightning])

  // Group matches by round_number
  const rounds = matches.reduce<Record<number, LightningMatchRead[]>>((acc, m) => {
    const group = acc[m.round_number] ?? []
    return { ...acc, [m.round_number]: [...group, m] }
  }, {})

  if (tournamentId === null) {
    return (
      <div className="overview-screen">
        <NavBar />
        <p className="overview-empty">Kein aktives Turnier.</p>
      </div>
    )
  }

  return (
    <div className="overview-screen">
      <NavBar />
      <div className="overview-content overview-content--single">
        <h1 className="overview-heading">Lightning Round</h1>
        {error !== null && (
          <p className="overview-error" role="alert">
            {error}
          </p>
        )}
        {noLightning ? (
          <p className="overview-empty">
            Die Lightning Round beginnt, wenn KO-Runden-Verlierer ausscheiden.
          </p>
        ) : (
          Object.entries(rounds).map(([roundNum, roundMatches]) => (
            <div key={roundNum} className="lightning-round">
              <h2 className="lightning-round-label">KO-Runde {roundNum}</h2>
              <ul className="lightning-list">
                {roundMatches.map(match => {
                  const isFinished = match.status === 'finished'
                  const winnerName =
                    isFinished && match.winner_id !== null
                      ? playerName(match.winner_id, playerMap)
                      : null
                  return (
                    <li key={match.match_id} className="lightning-item">
                      <span className="lightning-players">
                        {playerName(match.player1_id, playerMap)} vs{' '}
                        {playerName(match.player2_id, playerMap)}
                      </span>
                      <span className={`lightning-status lightning-status--${match.status}`}>
                        {STATUS_LABELS[match.status] ?? match.status}
                      </span>
                      {winnerName !== null && (
                        <span className="lightning-winner">Sieger: {winnerName}</span>
                      )}
                    </li>
                  )
                })}
              </ul>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
