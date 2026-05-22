import { useEffect, useState, useCallback } from 'react'
import { useTournament } from '../contexts/TournamentContext'
import { useWebSocket } from '../hooks/useWebSocket'
import { getKOBracket, getPlayers } from '../api/client'
import type { KOBracketResponse, KOMatchupRead, Player } from '../api/types'
import NavBar from '../components/NavBar'
import './overview.css'
import './BracketScreen.css'

function resolvePlayerName(id: number | null, playerMap: Record<number, Player>): string {
  if (id === null) return 'TBD'
  return playerMap[id]?.name ?? `#${id}`
}

interface BracketMatchProps {
  match: KOMatchupRead
  playerMap: Record<number, Player>
}

function BracketMatch({ match, playerMap }: BracketMatchProps) {
  const isFinished = match.status === 'finished'
  return (
    <div className="bracket-match" data-testid="bracket-match">
      <div
        className={`bracket-player${isFinished && match.winner_id === match.player1_id ? ' bracket-player--winner' : ''}`}
      >
        {resolvePlayerName(match.player1_id, playerMap)}
      </div>
      <div className="bracket-vs">vs</div>
      <div
        className={`bracket-player${isFinished && match.winner_id === match.player2_id ? ' bracket-player--winner' : ''}`}
      >
        {resolvePlayerName(match.player2_id, playerMap)}
      </div>
    </div>
  )
}

function TbdMatch({ label }: { label: string }) {
  return (
    <div className="bracket-match bracket-match--tbd" data-testid="bracket-match">
      <div className="bracket-player">TBD</div>
      <div className="bracket-vs">{label}</div>
      <div className="bracket-player">TBD</div>
    </div>
  )
}

export default function BracketScreen() {
  const { tournamentId } = useTournament()
  const [bracket, setBracket] = useState<KOBracketResponse | null>(null)
  const [playerMap, setPlayerMap] = useState<Record<number, Player>>({})
  const [error, setError] = useState<string | null>(null)
  const [noBracket, setNoBracket] = useState(false)

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

  const loadBracket = useCallback(() => {
    if (tournamentId === null) return
    getKOBracket(tournamentId)
      .then(data => {
        setBracket(data)
        setNoBracket(data.quarter_finals.length === 0)
      })
      .catch(() => {
        setNoBracket(true)
      })
  }, [tournamentId])

  useEffect(() => {
    loadBracket()
  }, [loadBracket])

  const { lastEvent } = useWebSocket('tournament', tournamentId ?? 0)

  useEffect(() => {
    if (lastEvent?.type === 'bracket_update') {
      loadBracket()
    }
  }, [lastEvent, loadBracket])

  // Always show 4 QF and 2 SF slots; fill missing ones with null (→ TBD)
  const qfSlots = Array.from<KOMatchupRead | null>(
    { length: 4 },
    (_, i) => bracket?.quarter_finals[i] ?? null,
  )
  const sfSlots = Array.from<KOMatchupRead | null>(
    { length: 2 },
    (_, i) => bracket?.semi_finals[i] ?? null,
  )

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
      <div className="overview-content">
        <section className="bracket-section">
          <h1 className="overview-heading">KO Bracket</h1>
          {error !== null && (
            <p className="overview-error" role="alert">
              {error}
            </p>
          )}
          {noBracket ? (
            <p className="overview-empty">Das KO-Bracket beginnt nach der Vorrunde.</p>
          ) : (
            <div className="bracket">
              <div className="bracket-round">
                <h2 className="bracket-round-label">Viertelfinale</h2>
                {qfSlots.map((match, i) =>
                  match !== null ? (
                    <BracketMatch key={`match-${match.match_id}`} match={match} playerMap={playerMap} />
                  ) : (
                    <TbdMatch key={`tbd-qf-${i}`} label="QF" />
                  ),
                )}
              </div>
              <div className="bracket-connector" aria-hidden="true" />
              <div className="bracket-round">
                <h2 className="bracket-round-label">Halbfinale</h2>
                {sfSlots.map((match, i) =>
                  match !== null ? (
                    <BracketMatch key={`match-${match.match_id}`} match={match} playerMap={playerMap} />
                  ) : (
                    <TbdMatch key={`tbd-sf-${i}`} label="SF" />
                  ),
                )}
              </div>
              <div className="bracket-connector" aria-hidden="true" />
              <div className="bracket-round bracket-round--finals">
                <h2 className="bracket-round-label">Finale</h2>
                {bracket?.final !== null && bracket?.final !== undefined ? (
                  <BracketMatch match={bracket.final} playerMap={playerMap} />
                ) : (
                  <TbdMatch label="Final" />
                )}
                <h2 className="bracket-round-label bracket-round-label--third">3. Platz</h2>
                {bracket?.third_place !== null && bracket?.third_place !== undefined ? (
                  <BracketMatch match={bracket.third_place} playerMap={playerMap} />
                ) : (
                  <TbdMatch label="3rd" />
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
