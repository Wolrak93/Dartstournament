import { useEffect, useState, useCallback } from 'react'
import { useTournament } from '../contexts/TournamentContext'
import { useWebSocket } from '../hooks/useWebSocket'
import { getStandings, getPlayers } from '../api/client'
import type { StandingEntry, Player } from '../api/types'
import NavBar from '../components/NavBar'
import NextMatchesPanel from '../components/NextMatchesPanel'
import './overview.css'
import './StandingsScreen.css'

export default function StandingsScreen() {
  const { tournamentId } = useTournament()
  const [standings, setStandings] = useState<StandingEntry[]>([])
  const [playerMap, setPlayerMap] = useState<Record<number, Player>>({})
  const [error, setError] = useState<string | null>(null)

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
  }, [loadStandings])

  const { lastEvent } = useWebSocket('tournament', tournamentId ?? 0)

  useEffect(() => {
    if (lastEvent?.type === 'standings_update') {
      loadStandings()
    }
  }, [lastEvent, loadStandings])

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
                    <td>{entry.reg_points.toFixed(2)}</td>
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
        </section>
        <NextMatchesPanel
          tournamentId={tournamentId}
          playerMap={playerMap}
          lastWsEvent={lastEvent}
        />
      </div>
    </div>
  )
}
