import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTournament } from '../contexts/TournamentContext'
import { useWebSocket } from '../hooks/useWebSocket'
import { getStandings, getPlayers, triggerNextRound, getNextMatches } from '../api/client'
import type { StandingEntry, Player } from '../api/types'
import NavBar from '../components/NavBar'
import './overview.css'
import './StandingsScreen.css'

export default function StandingsScreen() {
  const { tournamentId } = useTournament()
  const navigate = useNavigate()
  const [standings, setStandings] = useState<StandingEntry[]>([])
  const [playerMap, setPlayerMap] = useState<Record<number, Player>>({})
  const [error, setError] = useState<string | null>(null)
  const [nextRoundLoading, setNextRoundLoading] = useState(false)
  const [hasPendingMatches, setHasPendingMatches] = useState(true)

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

  const loadPendingMatches = useCallback(() => {
    if (tournamentId === null) return
    getNextMatches(tournamentId)
      .then(matches => setHasPendingMatches(matches.length > 0))
      .catch(() => setHasPendingMatches(false))
  }, [tournamentId])

  const loadStandings = useCallback(() => {
    if (tournamentId === null) return
    getStandings(tournamentId)
      .then(setStandings)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Fehler beim Laden'),
      )
  }, [tournamentId])

  useEffect(() => {
    loadStandings()
    loadPendingMatches()
  }, [loadStandings, loadPendingMatches])

  const { lastEvent } = useWebSocket('tournament', tournamentId ?? 0)

  useEffect(() => {
    if (lastEvent?.type === 'standings_update') {
      loadStandings()
      loadPendingMatches()
    }
  }, [lastEvent, loadStandings, loadPendingMatches])

  const handleNextRound = useCallback(() => {
    if (tournamentId === null) return
    setNextRoundLoading(true)
    setError(null)
    triggerNextRound(tournamentId)
      .then(() => {
        navigate('/next-matches')
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Fehler beim Erstellen der nächsten Runde'),
      )
      .finally(() => setNextRoundLoading(false))
  }, [tournamentId, navigate])

  if (tournamentId === null) {
    return (
      <div className="overview-screen">
        <NavBar />
        <p className="overview-empty">Kein aktives Turnier. Bitte zuerst ein Turnier starten.</p>
      </div>
    )
  }

  return (
    <div className="overview-screen">
      <NavBar />
      <div className="overview-content">
        <section className="standings-section">
          <h1 className="overview-heading">Vorrunde – Standings</h1>
          {error !== null && (
            <p className="overview-error" role="alert">
              {error}
            </p>
          )}
          <table className="standings-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Spieler</th>
                <th>Punkte</th>
                <th>Bonus</th>
                <th>Average</th>
              </tr>
            </thead>
            <tbody>
              {standings.map(entry => {
                let rowClass = 'standings-row'
                if (entry.rank <= 6) rowClass += ' standings-row--ko'
                else if (entry.rank <= 8) rowClass += ' standings-row--wildcard'
                return (
                  <tr key={entry.player_id} className={rowClass}>
                    <td className="standings-rank">{entry.rank}</td>
                    <td className="standings-name">
                      {playerMap[entry.player_id]?.name ?? `Spieler ${entry.player_id}`}
                    </td>
                    <td>{entry.total_points.toFixed(4)}</td>
                    <td>{entry.bonus_points}</td>
                    <td>{entry.avg_score.toFixed(2)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {standings.length > 0 && (
            <div className="standings-legend">
              <span className="legend-ko">■ Top 6: KO-Qualifikation</span>
              <span className="legend-wildcard">■ Platz 7–8: Wildcard</span>
            </div>
          )}
          {!hasPendingMatches && (
            <div className="standings-actions">
              <button
                className="btn-next-round"
                onClick={handleNextRound}
                disabled={nextRoundLoading}
              >
                {nextRoundLoading ? 'Wird geladen…' : 'Nächste Runde starten'}
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
