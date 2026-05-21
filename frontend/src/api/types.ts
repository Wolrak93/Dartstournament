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
// Bull throw
// ---------------------------------------------------------------------------

export interface BullThrowRequest {
  winner_id?: number | null
  best_player_id?: number | null
  best_opponent_id?: number | null
}

export interface BullThrowResponse {
  starting_player_id: number
  play_order: number[]
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

// ---------------------------------------------------------------------------
// Score entry (visits)
// ---------------------------------------------------------------------------

export interface VisitRequest {
  player_id: number
  dart1: number
  dart2: number
  dart3: number
  bounce_flags: boolean[]
  robin_hood_flags: boolean[]
}

export interface SpecialEventItem {
  event_type: string
  bonus_value: number
  count: number
}

export interface VisitResponse {
  visit_id: number
  player_id: number
  visit_number: number
  total: number
  is_bust: boolean
  remaining_after: number
  match_finished: boolean
  winner_id: number | null
  special_events: SpecialEventItem[]
}

export interface CheckoutSuggestion {
  darts: string[]
  is_finish: boolean
  leave: number
}

export interface MatchStateResponse {
  match_id: number
  status: MatchStatus
  round_type: RoundType
  starting_player_id: number | null
  current_player_id: number | null
  remaining_p1: number
  remaining_p2: number
  visit_count_p1: number
  visit_count_p2: number
  single_out_mode: boolean
  checkout_suggestion: CheckoutSuggestion | null
}
