import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTournaments, cloneTournament, deleteTournament } from '../api/client'
import type { Tournament, TournamentStatus } from '../api/types'
import { useTournament } from '../contexts/TournamentContext'
import './HomeScreen.css'

function statusLabel(status: TournamentStatus): string {
  switch (status) {
    case 'pending':
      return 'Ausstehend'
    case 'vorrunde':
      return 'Vorrunde'
    case 'ko':
      return 'KO-Runde'
    case 'finished':
      return 'Abgeschlossen'
  }
}

function targetRoute(status: TournamentStatus): string {
  switch (status) {
    case 'pending':
      return '/setup'
    case 'vorrunde':
      return '/standings'
    case 'ko':
      return '/bracket'
    case 'finished':
      return '/standings'
  }
}

function formatDate(isoString: string): string {
  const d = new Date(isoString)
  return d.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function HomeScreen() {
  const navigate = useNavigate()
  const { setTournamentId } = useTournament()

  const [tournaments, setTournaments] = useState<Tournament[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [cloningId, setCloningId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  useEffect(() => {
    getTournaments()
      .then(setTournaments)
      .catch((err: Error) => setLoadError(err.message))
  }, [])

  const handleResume = (tournament: Tournament) => {
    setTournamentId(tournament.id)
    navigate(targetRoute(tournament.status))
  }

  const handleClone = async (tournament: Tournament) => {
    setCloningId(tournament.id)
    setActionError(null)
    try {
      const newTournament = await cloneTournament(tournament.id)
      setTournamentId(newTournament.id)
      navigate(targetRoute(newTournament.status))
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Klonen fehlgeschlagen')
    } finally {
      setCloningId(null)
    }
  }

  const handleDeleteConfirm = async () => {
    if (confirmDeleteId === null) return
    setDeletingId(confirmDeleteId)
    setConfirmDeleteId(null)
    setActionError(null)
    try {
      await deleteTournament(confirmDeleteId)
      setTournaments((prev) => prev.filter((t) => t.id !== confirmDeleteId))
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Löschen fehlgeschlagen')
    } finally {
      setDeletingId(null)
    }
  }

  const tournamentToDelete = tournaments.find((t) => t.id === confirmDeleteId)

  return (
    <main className="home-screen">
      <h1 className="home-title">Backsberger Open</h1>

      <button
        type="button"
        className="home-new-btn"
        onClick={() => navigate('/setup')}
      >
        + Neues Turnier erstellen
      </button>

      {loadError && (
        <p className="home-error" role="alert">
          Turniere konnten nicht geladen werden: {loadError}
        </p>
      )}

      {actionError && (
        <p className="home-error" role="alert">
          {actionError}
        </p>
      )}

      {!loadError && tournaments.length === 0 && (
        <p className="home-empty">Noch keine Turniere vorhanden.</p>
      )}

      {tournaments.length > 0 && (
        <section className="home-list">
          <h2 className="home-section-title">Bisherige Turniere</h2>
          <ul className="tournament-list">
            {tournaments.map((t) => (
              <li key={t.id} className="tournament-card">
                <div className="tournament-card__info">
                  <span className="tournament-card__name">
                    {t.name ?? `Turnier vom ${formatDate(t.created_at)}`}
                  </span>
                  <span className="tournament-card__meta">
                    {t.player_count} Spieler &middot; {t.mode === 'swiss' ? 'Swiss' : 'Feste Auslosung'}
                    &middot; {formatDate(t.created_at)}
                  </span>
                </div>
                <div className="tournament-card__right">
                  <span className={`status-badge status-badge--${t.status}`}>
                    {statusLabel(t.status)}
                  </span>
                  <div className="tournament-card__actions">
                    <button
                      type="button"
                      className="card-btn card-btn--primary"
                      onClick={() => handleResume(t)}
                    >
                      Fortsetzen
                    </button>
                    <button
                      type="button"
                      className="card-btn card-btn--secondary"
                      disabled={cloningId === t.id}
                      onClick={() => handleClone(t)}
                    >
                      {cloningId === t.id ? 'Klone...' : 'Klonen'}
                    </button>
                    <button
                      type="button"
                      className="card-btn card-btn--danger"
                      disabled={deletingId === t.id}
                      onClick={() => setConfirmDeleteId(t.id)}
                    >
                      {deletingId === t.id ? 'Lösche...' : 'Löschen'}
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {confirmDeleteId !== null && (
        <div className="delete-modal-overlay" onClick={() => setConfirmDeleteId(null)}>
          <div className="delete-modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="delete-modal__title">Turnier löschen?</h2>
            <p className="delete-modal__body">
              Soll das Turnier{' '}
              <strong>
                {tournamentToDelete?.name ?? `vom ${tournamentToDelete ? formatDate(tournamentToDelete.created_at) : ''}`}
              </strong>{' '}
              wirklich unwiderruflich gelöscht werden?
              <br />
              Alle Spiele, Ergebnisse und Ereignisse gehen verloren.
            </p>
            <div className="delete-modal__actions">
              <button
                type="button"
                className="card-btn card-btn--secondary"
                onClick={() => setConfirmDeleteId(null)}
              >
                Abbrechen
              </button>
              <button
                type="button"
                className="card-btn card-btn--danger"
                onClick={handleDeleteConfirm}
              >
                Ja, löschen
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
