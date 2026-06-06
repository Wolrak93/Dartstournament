import type {
  Player,
  Tournament,
  TournamentDetail,
  TournamentCreateRequest,
  StandingEntry,
  MatchRead,
  BullThrowRequest,
  BullThrowResponse,
  KOBracketResponse,
  LightningResponse,
  VisitRequest,
  VisitResponse,
  VisitHistoryItem,
  MatchStateResponse,
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

async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { method: 'DELETE' })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error((err as { detail?: string }).detail ?? response.statusText)
  }
  return response.json() as Promise<T>
}

async function apiDeleteNoContent(path: string): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, { method: 'DELETE' })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error((err as { detail?: string }).detail ?? response.statusText)
  }
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

export const getMatch = (matchId: number): Promise<MatchRead> =>
  apiGet<MatchRead>(`/matches/${matchId}`)

// ---------------------------------------------------------------------------
// Tournament endpoints
// ---------------------------------------------------------------------------

export const getTournaments = (): Promise<Tournament[]> =>
  apiGet<Tournament[]>('/tournaments')

export const getTournamentById = (tournamentId: number): Promise<TournamentDetail> =>
  apiGet<TournamentDetail>(`/tournaments/${tournamentId}`)

export const startKOPhase = (tournamentId: number): Promise<KOBracketResponse> =>
  apiPost<KOBracketResponse>(`/tournaments/${tournamentId}/ko/start`)

export const createTournament = (body: TournamentCreateRequest): Promise<Tournament> =>
  apiPost<Tournament, TournamentCreateRequest>('/tournaments', body)

export const cloneTournament = (tournamentId: number): Promise<Tournament> =>
  apiPost<Tournament>(`/tournaments/${tournamentId}/clone`)

export const startTournament = (tournamentId: number): Promise<unknown> =>
  apiPost<unknown>(`/tournaments/${tournamentId}/start`)

export const recordBullThrow = (
  matchId: number,
  body: BullThrowRequest,
): Promise<BullThrowResponse> =>
  apiPost<BullThrowResponse, BullThrowRequest>(`/matches/${matchId}/bull-throw`, body)

export const startMatch = (matchId: number): Promise<unknown> =>
  apiPost<unknown>(`/matches/${matchId}/start`)

export const getStandings = (tournamentId: number): Promise<StandingEntry[]> =>
  apiGet<StandingEntry[]>(`/tournaments/${tournamentId}/standings`)

export const getNextMatches = (tournamentId: number): Promise<MatchRead[]> =>
  apiGet<MatchRead[]>(`/tournaments/${tournamentId}/matches/next`)

export const getKOBracket = (tournamentId: number): Promise<KOBracketResponse> =>
  apiGet<KOBracketResponse>(`/tournaments/${tournamentId}/ko/bracket`)

export const getLightning = (tournamentId: number): Promise<LightningResponse> =>
  apiGet<LightningResponse>(`/tournaments/${tournamentId}/lightning`)

export const getMatchState = (matchId: number): Promise<MatchStateResponse> =>
  apiGet<MatchStateResponse>(`/matches/${matchId}/state`)

export const triggerNextRound = (tournamentId: number): Promise<MatchRead[]> =>
  apiPost<MatchRead[]>(`/tournaments/${tournamentId}/next-round`)

export const recordVisit = (matchId: number, body: VisitRequest): Promise<VisitResponse> =>
  apiPost<VisitResponse, VisitRequest>(`/matches/${matchId}/visits`, body)

export const getMatchVisits = (matchId: number): Promise<VisitHistoryItem[]> =>
  apiGet<VisitHistoryItem[]>(`/matches/${matchId}/visits`)

export const undoLastVisit = (matchId: number): Promise<{ undone_visit_id: number; match_id: number }> =>
  apiDelete(`/matches/${matchId}/visits/last`)

export const deleteTournament = (tournamentId: number): Promise<void> =>
  apiDeleteNoContent(`/tournaments/${tournamentId}`)
