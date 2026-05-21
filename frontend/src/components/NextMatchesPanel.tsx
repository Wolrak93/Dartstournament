import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getNextMatches } from '../api/client'
import type { MatchRead, Player } from '../api/types'
import type { WsEvent } from '../hooks/useWebSocket'
import './NextMatchesPanel.css'

interface NextMatchesPanelProps {
  tournamentId: number
  playerMap: Record<number, Player>
  lastWsEvent: WsEvent | null
}

const ROUND_LABELS: Record<string, string> = {
  vorrunde: 'Vorrunde',
  ko: 'KO-Runde',
  lightning: 'Lightning',
}

function matchLink(match: MatchRead): string {
  return match.status === 'in_progress' ? `/score/${match.id}` : `/bull-throw/${match.id}`
}

function playerName(id: number, map: Record<number, Player>): string {
  return map[id]?.name ?? `#${id}`
}

function matchLabel(match: MatchRead, map: Record<number, Player>): string {
  const p3 = match.player3_id !== null ? playerName(match.player3_id, map) : null
  const p4 = match.player4_id !== null ? playerName(match.player4_id, map) : null
  if (p3 !== null && p4 !== null) {
    return `${playerName(match.player1_id, map)} & ${p3} vs ${playerName(match.player2_id, map)} & ${p4}`
  }
  return `${playerName(match.player1_id, map)} vs ${playerName(match.player2_id, map)}`
}

export default function NextMatchesPanel({
  tournamentId,
  playerMap,
  lastWsEvent,
}: NextMatchesPanelProps) {
  const [matches, setMatches] = useState<MatchRead[]>([])

  const loadMatches = useCallback(() => {
    getNextMatches(tournamentId)
      .then(setMatches)
      .catch(() => setMatches([]))
  }, [tournamentId])

  useEffect(() => {
    loadMatches()
  }, [loadMatches])

  useEffect(() => {
    if (
      lastWsEvent?.type === 'standings_update' ||
      lastWsEvent?.type === 'bracket_update' ||
      lastWsEvent?.type === 'match_finished'
    ) {
      loadMatches()
    }
  }, [lastWsEvent, loadMatches])

  if (matches.length === 0) return null

  return (
    <aside className="next-matches-panel">
      <h2 className="next-matches-title">Nächste Matches</h2>
      <ul className="next-matches-list">
        {matches.map(match => (
          <li key={match.id} className="next-match-item">
            <span className="next-match-round">
              {ROUND_LABELS[match.round_type] ?? match.round_type} R{match.round_number}
            </span>
            <span className="next-match-players">{matchLabel(match, playerMap)}</span>
            <Link
              to={matchLink(match)}
              className={`next-match-btn${match.status === 'in_progress' ? ' next-match-btn--active' : ''}`}
            >
              {match.status === 'in_progress' ? 'Fortsetzen' : 'Starten'}
            </Link>
          </li>
        ))}
      </ul>
    </aside>
  )
}
