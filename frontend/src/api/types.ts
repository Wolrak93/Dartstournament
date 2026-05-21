// TypeScript interfaces mirroring the backend Pydantic schemas.

export type TournamentMode = 'swiss' | 'fixed'
export type TournamentStatus = 'pending' | 'vorrunde' | 'ko' | 'finished'
export type MatchStatus = 'pending' | 'bull_throw' | 'in_progress' | 'finished'
export type RoundType = 'vorrunde' | 'ko' | 'lightning'

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

// ---------------------------------------------------------------------------
// Standings
// ---------------------------------------------------------------------------

export interface StandingEntry {
  rank: number
  player_id: number
  reg_points: number
  bonus_points: number
  avg_score: number
  total_points: number
}

// ---------------------------------------------------------------------------
// Matches
// ---------------------------------------------------------------------------

export interface MatchRead {
  id: number
  tournament_id: number
  round_type: RoundType
  round_number: number
  player1_id: number
  player2_id: number
  player3_id: number | null
  player4_id: number | null
  starting_score_p1: number
  starting_score_p2: number
  winner_id: number | null
  starting_player_id: number | null
  status: MatchStatus
}

// ---------------------------------------------------------------------------
// KO Bracket
// ---------------------------------------------------------------------------

export interface QualifiedPlayerRead {
  player_id: number
  seed: number
  qualified_via: 'regular' | 'bonus'
}

export interface KOMatchupRead {
  match_id: number
  stage: 'qf' | 'sf' | 'final' | 'third_place'
  player1_id: number
  player2_id: number
  starting_score_p1: number
  starting_score_p2: number
  status: MatchStatus
  winner_id: number | null
}

export interface KOBracketResponse {
  qualified_players: QualifiedPlayerRead[]
  quarter_finals: KOMatchupRead[]
  semi_finals: KOMatchupRead[]
  final: KOMatchupRead | null
  third_place: KOMatchupRead | null
  lightning_player_ids: number[]
}

// ---------------------------------------------------------------------------
// Lightning Round
// ---------------------------------------------------------------------------

export interface LightningMatchRead {
  match_id: number
  round_number: number
  player1_id: number
  player2_id: number
  status: MatchStatus
  winner_id: number | null
}

export interface LightningResponse {
  matches: LightningMatchRead[]
}
