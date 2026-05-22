import { useEffect, useState } from 'react'
import { useTournament } from '../contexts/TournamentContext'
import { useWebSocket } from '../hooks/useWebSocket'
import { getPlayers } from '../api/client'
import type { Player } from '../api/types'
import NavBar from '../components/NavBar'
import NextMatchesPanel from '../components/NextMatchesPanel'
import './overview.css'
import './NextMatchesScreen.css'

export default function NextMatchesScreen() {
  const { tournamentId } = useTournament()
  const [playerMap, setPlayerMap] = useState<Record<number, Player>>({})

  useEffect(() => {
    getPlayers()
      .then(players => {
        const map: Record<number, Player> = {}
        players.forEach(p => {
          map[p.id] = p
        })
        setPlayerMap(map)
      })
      .catch(() => {})
  }, [])

  const { lastEvent } = useWebSocket('tournament', tournamentId ?? 0)

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
      <div className="nm-screen-body">
        <NextMatchesPanel
          tournamentId={tournamentId}
          playerMap={playerMap}
          lastWsEvent={lastEvent}
        />
      </div>
    </div>
  )
}
