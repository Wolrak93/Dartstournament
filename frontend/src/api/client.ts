import type {
  Player,
  Tournament,
  TournamentCreateRequest,
  StandingEntry,
  MatchRead,
  KOBracketResponse,
  LightningResponse,
} from './types'

export const API_BASE: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

// Derive WebSocket base URL from the HTTP base URL.
export const WS_BASE: string = API_BASE.replace(/^http/, 'ws')

// Returns the full URL for a player photo served as a static file by the backend.
export const playerPhotoUrl = (photoPath: string): string =>
  `${API_BASE}/static/${photoPath}`

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`)
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error((err as { detail?: string }).detail ?? response.statusText)
  }
  return response.json() as Promise<T>
}

async function apiPost<T, B = unknown>(path: string, body?: B): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error((err as { detail?: string }).detail ?? response.statusText)
  }
  return response.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Player endpoints
// ---------------------------------------------------------------------------

export const getPlayers = (): Promise<Player[]> => apiGet<Player[]>('/players')

// ---------------------------------------------------------------------------
// Tournament endpoints
// ---------------------------------------------------------------------------

export const createTournament = (body: TournamentCreateRequest): Promise<Tournament> =>
  apiPost<Tournament, TournamentCreateRequest>('/tournaments', body)

export const startTournament = (tournamentId: number): Promise<unknown> =>
  apiPost<unknown>(`/tournaments/${tournamentId}/start`)

export const getStandings = (tournamentId: number): Promise<StandingEntry[]> =>
  apiGet<StandingEntry[]>(`/tournaments/${tournamentId}/standings`)

export const getNextMatches = (tournamentId: number): Promise<MatchRead[]> =>
  apiGet<MatchRead[]>(`/tournaments/${tournamentId}/matches/next`)

export const getKOBracket = (tournamentId: number): Promise<KOBracketResponse> =>
  apiGet<KOBracketResponse>(`/tournaments/${tournamentId}/ko/bracket`)

export const getLightning = (tournamentId: number): Promise<LightningResponse> =>
  apiGet<LightningResponse>(`/tournaments/${tournamentId}/lightning`)
