import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getNextMatches, playerPhotoUrl } from '../api/client'
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
  if (match.status === 'in_progress') return `/score/${match.id}`
  if (
    match.status === 'pending' &&
    (match.round_type === 'ko' || match.round_type === 'lightning')
  )
    return `/walkon/${match.id}`
  return `/bull-throw/${match.id}`
}

interface PlayerSlotProps {
  id: number
  playerMap: Record<number, Player>
}

function PlayerSlot({ id, playerMap }: PlayerSlotProps) {
  const player = playerMap[id]
  return (
    <div className="nm-player">
      {player?.photo_path != null ? (
        <img
          src={playerPhotoUrl(player.photo_path)}
          alt={player.name}
          className="nm-photo"
        />
      ) : (
        <div className="nm-photo nm-photo--placeholder">
          {player?.name?.[0]?.toUpperCase() ?? '?'}
        </div>
      )}
      <span className="nm-player-name">{player?.name ?? `#${id}`}</span>
    </div>
  )
}

interface MatchCardProps {
  match: MatchRead
  playerMap: Record<number, Player>
}

function MatchCard({ match, playerMap }: MatchCardProps) {
  const isDoubles = match.player3_id !== null && match.player4_id !== null
  const isActive = match.status === 'in_progress'

  return (
    <div className={`nm-card${isActive ? ' nm-card--active' : ''}`}>
      <div className="nm-card-header">
        <span className="nm-round-label">
          {ROUND_LABELS[match.round_type] ?? match.round_type} · Runde {match.round_number}
        </span>
      </div>

      <div className="nm-matchup">
        <div className="nm-team">
          <PlayerSlot id={match.player1_id} playerMap={playerMap} />
          {isDoubles && match.player3_id !== null && (
            <PlayerSlot id={match.player3_id} playerMap={playerMap} />
          )}
        </div>

        <div className="nm-vs">VS</div>

        <div className="nm-team">
          <PlayerSlot id={match.player2_id} playerMap={playerMap} />
          {isDoubles && match.player4_id !== null && (
            <PlayerSlot id={match.player4_id} playerMap={playerMap} />
          )}
        </div>
      </div>

      <div className="nm-card-footer">
        <Link
          to={matchLink(match)}
          className={`nm-start-btn${isActive ? ' nm-start-btn--active' : ''}`}
        >
          {isActive ? 'Fortsetzen' : 'Starten'}
        </Link>
      </div>
    </div>
  )
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

  if (matches.length === 0) {
    return (
      <div className="nm-panel">
        <h2 className="nm-title">Nächste Matches</h2>
        <p className="nm-empty">Keine ausstehenden Matches.</p>
      </div>
    )
  }

  return (
    <div className="nm-panel">
      <h2 className="nm-title">Nächste Matches</h2>
      <ul className="nm-list">
        {matches.map(match => (
          <li key={match.id}>
            <MatchCard match={match} playerMap={playerMap} />
          </li>
        ))}
      </ul>
    </div>
  )
}
