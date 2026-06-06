import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getPlayers, createTournament, startTournament, playerPhotoUrl } from '../api/client'
import type { Player, TournamentMode } from '../api/types'
import { useTournament } from '../contexts/TournamentContext'
import './SetupScreen.css'

const MIN_PLAYERS = 9
const MAX_PLAYERS = 13

export default function SetupScreen() {
  const navigate = useNavigate()
  const { setTournamentId } = useTournament()

  const [players, setPlayers] = useState<Player[]>([])
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [mode, setMode] = useState<TournamentMode>('swiss')
  const [loading, setLoading] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  useEffect(() => {
    getPlayers()
      .then(setPlayers)
      .catch((err: Error) => setFetchError(err.message))
  }, [])

  const togglePlayer = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const selectionError: string | null = (() => {
    if (selected.size < MIN_PLAYERS)
      return `Mindestens ${MIN_PLAYERS} Spieler auswählen (aktuell: ${selected.size})`
    if (selected.size > MAX_PLAYERS)
      return `Höchstens ${MAX_PLAYERS} Spieler auswählen (aktuell: ${selected.size})`
    return null
  })()

  const handleStart = async () => {
    if (selectionError) return
    setLoading(true)
    setSubmitError(null)
    try {
      const tournament = await createTournament({
        player_ids: [...selected],
        mode,
      })
      await startTournament(tournament.id)
      setTournamentId(tournament.id)
      navigate('/standings')
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Unbekannter Fehler')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="setup-screen">
      <h1 className="setup-title">Backsberger Open</h1>
      <h2 className="setup-subtitle">Neues Turnier</h2>

      <button
        type="button"
        className="setup-back-btn"
        onClick={() => navigate('/')}
      >
        ← Zurück zur Übersicht
      </button>

      {fetchError && (
        <p className="setup-error" role="alert">
          Spieler konnten nicht geladen werden: {fetchError}
        </p>
      )}

      <section className="setup-players">
        <h3 className="setup-section-title">
          Spieler auswählen ({selected.size}/{MAX_PLAYERS})
        </h3>

        <ul className="player-list">
          {players.map((player) => (
            <li key={player.id}>
              <label
                className={`player-card${selected.has(player.id) ? ' player-card--selected' : ''}`}
              >
                <input
                  type="checkbox"
                  className="player-checkbox"
                  checked={selected.has(player.id)}
                  onChange={() => togglePlayer(player.id)}
                />
                {player.photo_path && (
                  <img
                    src={playerPhotoUrl(player.photo_path)}
                    alt={player.name}
                    className="player-photo"
                  />
                )}
                <span className="player-name">{player.name}</span>
              </label>
            </li>
          ))}
        </ul>

        {selectionError && (
          <p className="setup-validation" role="alert">
            {selectionError}
          </p>
        )}
      </section>

      <section className="setup-mode">
        <h3 className="setup-section-title">Spielmodus</h3>
        <div className="mode-toggle">
          <button
            type="button"
            className={`mode-btn${mode === 'swiss' ? ' mode-btn--active' : ''}`}
            onClick={() => setMode('swiss')}
          >
            Swiss
          </button>
          <button
            type="button"
            className={`mode-btn${mode === 'fixed' ? ' mode-btn--active' : ''}`}
            onClick={() => setMode('fixed')}
          >
            Feste Auslosung
          </button>
        </div>
      </section>

      {submitError && (
        <p className="setup-error" role="alert">
          {submitError}
        </p>
      )}

      <button
        type="button"
        className="start-btn"
        disabled={!!selectionError || loading}
        onClick={handleStart}
      >
        {loading ? 'Starte...' : 'Turnier starten'}
      </button>
    </main>
  )
}
