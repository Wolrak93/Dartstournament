import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { API_BASE, getMatch, getPlayers, getStandings, playerPhotoUrl } from '../api/client'
import type { MatchRead, Player, StandingEntry } from '../api/types'
import { useTournament } from '../contexts/TournamentContext'
import profiles from '../data/playerProfiles.json'
import './WalkOnScreen.css'

type WalkOnPhase = 'p1-idle' | 'p1-playing' | 'p2-idle' | 'p2-playing'

interface PlayerProfile {
  nickname: string
  funFact: string
  bestPerformance: string
}

const playerProfiles = profiles as Record<string, PlayerProfile>

export default function WalkOnScreen() {
  const { matchId } = useParams<{ matchId: string }>()
  const navigate = useNavigate()
  const { tournamentId } = useTournament()

  const [match, setMatch] = useState<MatchRead | null>(null)
  const [playerMap, setPlayerMap] = useState<Map<number, Player>>(new Map())
  const [standings, setStandings] = useState<StandingEntry[]>([])
  const [phase, setPhase] = useState<WalkOnPhase>('p1-idle')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    if (!matchId) return
    const id = parseInt(matchId, 10)
    const standingsPromise =
      tournamentId != null ? getStandings(tournamentId) : Promise.resolve([])
    Promise.all([getMatch(id), getPlayers(), standingsPromise])
      .then(([matchData, playerList, standingsList]) => {
        setMatch(matchData)
        setPlayerMap(new Map(playerList.map((p) => [p.id, p])))
        setStandings(standingsList)
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Fehler beim Laden')
      })
      .finally(() => setLoading(false))
  }, [matchId, tournamentId])

  useEffect(
    () => () => {
      audioRef.current?.pause()
    },
    [],
  )

  function stopMusic(): void {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
    }
  }

  function startMusic(player: Player): void {
    stopMusic()
    if (!player.music_path) return
    const audio = new Audio(`${API_BASE}/static/${player.music_path}`)
    audioRef.current = audio
    audio.play().catch((err: unknown) => {
      console.warn('[WalkOnScreen] Music playback failed:', err)
    })
  }

  function handleButton(): void {
    if (!match) return
    const p1 = playerMap.get(match.player1_id)
    const p2 = playerMap.get(match.player2_id)
    switch (phase) {
      case 'p1-idle':
        if (p1) startMusic(p1)
        setPhase('p1-playing')
        break
      case 'p1-playing':
        stopMusic()
        setPhase('p2-idle')
        break
      case 'p2-idle':
        if (p2) startMusic(p2)
        setPhase('p2-playing')
        break
      case 'p2-playing':
        stopMusic()
        navigate(`/bull-throw/${matchId}`)
        break
    }
  }

  if (loading) return <div className="walkon-loading">Laden…</div>
  if (error || !match) {
    return <div className="walkon-error">{error ?? 'Match nicht gefunden'}</div>
  }

  const activePlayerId = phase.startsWith('p1') ? match.player1_id : match.player2_id
  const activePlayer = playerMap.get(activePlayerId)
  const standingEntry = standings.find((s) => s.player_id === activePlayerId)
  const profile: PlayerProfile | undefined = activePlayer
    ? playerProfiles[activePlayer.name]
    : undefined
  const avg = standingEntry ? standingEntry.avg_score.toFixed(1) : '—'
  const wins = standingEntry ? String(standingEntry.wins) : '—'
  const losses = standingEntry
    ? String(standingEntry.games_played - standingEntry.wins)
    : '—'
  const buttonLabel = phase.endsWith('idle') ? '▶ Musik starten' : 'Ready — Weiter'

  return (
    <div className="walkon-screen">
      <div className="walkon-photo-col">
        {activePlayer?.photo_path != null ? (
          <img
            src={playerPhotoUrl(activePlayer.photo_path)}
            alt={activePlayer.name}
            className="walkon-photo"
          />
        ) : (
          <div className="walkon-photo-placeholder">📷</div>
        )}
        <div className="walkon-photo-fade" />
      </div>

      <div className="walkon-info-col">
        <div>
          <div className="walkon-name">{activePlayer?.name ?? '—'}</div>
          {profile?.nickname && (
            <div className="walkon-nickname">"{profile.nickname}"</div>
          )}
        </div>

        <div className="walkon-divider" />

        {profile?.funFact && (
          <div>
            <div className="walkon-label">Fun Fact</div>
            <div className="walkon-text">{profile.funFact}</div>
          </div>
        )}

        {profile?.bestPerformance && (
          <div>
            <div className="walkon-label">Best Performance</div>
            <div className="walkon-best">{profile.bestPerformance}</div>
          </div>
        )}

        <div className="walkon-stats">
          <div className="walkon-stat">
            <div className="walkon-label">Average</div>
            <div className="walkon-stat-value walkon-stat-value--avg">{avg}</div>
            <div className="walkon-stat-sub">dieses Turnier</div>
          </div>
          <div className="walkon-stat">
            <div className="walkon-label">Siege</div>
            <div className="walkon-stat-value walkon-stat-value--wins">{wins}</div>
            <div className="walkon-stat-sub">dieses Turnier</div>
          </div>
          <div className="walkon-stat">
            <div className="walkon-label">Niederlagen</div>
            <div className="walkon-stat-value walkon-stat-value--losses">{losses}</div>
            <div className="walkon-stat-sub">dieses Turnier</div>
          </div>
        </div>
      </div>

      <button className="walkon-btn" onClick={handleButton}>
        {buttonLabel}
      </button>
    </div>
  )
}
