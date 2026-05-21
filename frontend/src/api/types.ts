// TypeScript interfaces mirroring the backend Pydantic schemas.

export type TournamentMode = 'swiss' | 'fixed'
export type TournamentStatus = 'pending' | 'vorrunde' | 'ko' | 'finished'

export interface Player {
  id: number
  name: string
  photo_path: string | null
  music_path: string | null
  championship_count: number
}

export interface Tournament {
  id: number
  created_at: string
  player_count: number
  mode: TournamentMode
  status: TournamentStatus
}

export interface TournamentCreateRequest {
  player_ids: number[]
  mode: TournamentMode
}
