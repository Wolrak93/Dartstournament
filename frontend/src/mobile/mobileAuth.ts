const TOKEN_KEY = 'mobile_token'
const PLAYER_ID_KEY = 'mobile_player_id'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string, playerId?: number): void {
  localStorage.setItem(TOKEN_KEY, token)
  if (playerId !== undefined) {
    localStorage.setItem(PLAYER_ID_KEY, String(playerId))
  }
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(PLAYER_ID_KEY)
}

export function isLoggedIn(): boolean {
  return getToken() !== null
}

export function getStoredPlayerId(): number | null {
  const val = localStorage.getItem(PLAYER_ID_KEY)
  return val !== null ? Number(val) : null
}
