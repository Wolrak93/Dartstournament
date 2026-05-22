"""Vorrunde (preliminary round) logic for the Backsberger Open.

Supports two scheduling modes:
- fixed: all pairings generated upfront at tournament start
- swiss: pairings generated round-by-round based on current standings

Player count rules:
- 10 or 12 players → doubles mode (2v2, rotating partners)
- 9, 11, 13 players → singles mode
"""

from __future__ import annotations

import random
from dataclasses import (
    dataclass,
    field,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.events import DetectedEvent

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class MatchPairing:
    """A single match in the schedule.

    Singles:  team1=[p1], team2=[p2]
    Doubles:  team1=[p1, p3], team2=[p2, p4]
    """

    round_number: int
    team1: list[int]  # player IDs
    team2: list[int]  # player IDs


@dataclass
class PlayerStanding:
    """Running points for one player during the Vorrunde."""

    player_id: int
    reg_points: float = 0.0
    bonus_points: int = 0
    total_score: int = 0  # cumulative dart score (for average calculation)
    total_visits: int = 0  # number of visits thrown (for average calculation)

    @property
    def avg_score(self) -> float:
        """3-dart average: total points scored divided by number of visits."""
        if self.total_visits == 0:
            return 0.0
        return self.total_score / self.total_visits

    @property
    def avg_bonus(self) -> float:
        """Average contribution to regular points (average / 100)."""
        return self.avg_score / 100.0

    @property
    def sort_key(self) -> tuple[float, int]:
        """Primary sort: reg_points + avg_bonus desc; secondary: bonus_points desc."""
        return (self.reg_points + self.avg_bonus, self.bonus_points)


# ---------------------------------------------------------------------------
# Helpers: mode & validation
# ---------------------------------------------------------------------------


def is_doubles_mode(player_count: int) -> bool:
    """Return True when the tournament runs in doubles mode (10 or 12 players)."""
    return player_count in {10, 12}


def validate_player_count(player_count: int) -> None:
    """Raise ValueError when player_count is outside the supported range 9–13."""
    if player_count < 9 or player_count > 13:
        raise ValueError(
            f"Player count must be between 9 and 13, got {player_count}."
        )


def target_matches_per_player(player_count: int) -> int:
    """Return the target number of matches per player for the Vorrunde.

    Doubles mode (10, 12): 6 matches each.
    Singles mode (9, 11, 13): 3 or 4 matches each (returns 4 as upper bound;
    actual schedules may give some players 3 matches).
    """
    validate_player_count(player_count)
    return 6 if is_doubles_mode(player_count) else 4


# ---------------------------------------------------------------------------
# Fixed draw — singles
# ---------------------------------------------------------------------------


def _generate_singles_fixed_draw(player_ids: list[int]) -> list[MatchPairing]:
    """Generate a fixed draw schedule for singles mode.

    Uses a round-robin rotation (Berger tables approach) to produce a
    balanced schedule.  With an odd number of players the algorithm inserts
    a dummy bye player so every player gets at most 1 bye per schedule run.
    The schedule is then trimmed so each player gets at most 4 real matches.

    Returns a list of MatchPairing objects ordered by round_number.
    """
    ids = list(player_ids)
    n = len(ids)

    # Insert a dummy (None) for bye handling when n is odd
    bye_id = -1  # sentinel for bye
    if n % 2 == 1:
        ids.append(bye_id)

    total = len(ids)
    half = total // 2

    # Round-robin rotation: fix ids[0], rotate the rest
    pairings: list[MatchPairing] = []
    schedule = list(ids)

    for round_num in range(1, total):
        round_pairs: list[MatchPairing] = []
        for i in range(half):
            a = schedule[i]
            b = schedule[total - 1 - i]
            if a != bye_id and b != bye_id:
                round_pairs.append(
                    MatchPairing(
                        round_number=round_num,
                        team1=[a],
                        team2=[b],
                    )
                )
        pairings.extend(round_pairs)
        # Rotate: keep index 0 fixed, shift the rest left by one
        schedule = [schedule[0]] + [schedule[-1]] + schedule[1:-1]

    # Trim: keep only matches so each player has at most 4 appearances
    return _trim_to_max_appearances(pairings, max_per_player=4)


def _trim_to_max_appearances(
    pairings: list[MatchPairing], max_per_player: int
) -> list[MatchPairing]:
    """Filter pairings so no player appears more than max_per_player times."""
    counts: dict[int, int] = {}
    result: list[MatchPairing] = []
    for p in pairings:
        all_ids = p.team1 + p.team2
        if all(counts.get(pid, 0) < max_per_player for pid in all_ids):
            result.append(p)
            for pid in all_ids:
                counts[pid] = counts.get(pid, 0) + 1
    return result


# ---------------------------------------------------------------------------
# Fixed draw — doubles
# ---------------------------------------------------------------------------


def _try_doubles_schedule(
    ids: list[int],
    target_total: int,
    seed: int,
) -> list[tuple[list[int], list[int]]] | None:
    """One randomised attempt to build a complete doubles schedule.

    Returns the list of (team1, team2) raw matches if successful, else None.
    """
    rng = random.Random(seed)

    partner_history: dict[int, set[int]] = {pid: set() for pid in ids}
    match_count: dict[int, int] = {pid: 0 for pid in ids}
    raw_matches: list[tuple[list[int], list[int]]] = []

    while len(raw_matches) < target_total:
        # Sort by match_count; within the same count, shuffle for randomness.
        available = sorted(ids, key=lambda p: match_count[p])
        available = [p for p in available if match_count[p] < 6]

        if len(available) < 4:
            break

        # Add randomness within equal-count groups so different seeds yield
        # different orderings and avoid the same greedy dead-end each time.
        min_count = match_count[available[0]]
        head = [p for p in available if match_count[p] == min_count]
        tail = [p for p in available if match_count[p] > min_count]
        rng.shuffle(head)
        available = head + tail

        found = False
        for i, a in enumerate(available):
            for j in range(i + 1, len(available)):
                b = available[j]
                if b in partner_history[a]:
                    continue
                rest = [p for p in available if p not in {a, b}]
                for k, c in enumerate(rest):
                    for d in rest[k + 1 :]:
                        if d in partner_history[c]:
                            continue
                        raw_matches.append(([a, b], [c, d]))
                        partner_history[a].add(b)
                        partner_history[b].add(a)
                        partner_history[c].add(d)
                        partner_history[d].add(c)
                        match_count[a] += 1
                        match_count[b] += 1
                        match_count[c] += 1
                        match_count[d] += 1
                        found = True
                        break
                    if found:
                        break
                if found:
                    break
            if found:
                break

        if not found:
            break

    if len(raw_matches) == target_total:
        return raw_matches
    return None


def _generate_doubles_fixed_draw(player_ids: list[int]) -> list[MatchPairing]:
    """Generate a fixed draw schedule for doubles mode (10 or 12 players).

    Rules:
    - Each player plays 6 matches.
    - Each player has a different partner in every match (no repeat partners).

    Strategy: randomised greedy with retries.  A purely deterministic greedy
    can reach a dead-end due to partner constraints; restarting with a
    different random seed quickly finds a valid schedule.
    """
    ids = list(player_ids)
    n = len(ids)
    target_total = n * 6 // 4  # 15 for n=10, 18 for n=12

    raw_matches: list[tuple[list[int], list[int]]] | None = None
    for seed in range(200):
        raw_matches = _try_doubles_schedule(ids, target_total, seed)
        if raw_matches is not None:
            break

    if raw_matches is None:  # pragma: no cover
        raise RuntimeError("Could not generate a valid doubles schedule.")

    # Assign round numbers: greedy bin-packing so no player appears twice per round.
    pairings: list[MatchPairing] = []
    round_slots: list[set[int]] = []

    for team1, team2 in raw_matches:
        all_four = set(team1 + team2)
        assigned = False
        for idx, slot in enumerate(round_slots):
            if not (slot & all_four):
                slot |= all_four
                pairings.append(
                    MatchPairing(round_number=idx + 1, team1=team1, team2=team2)
                )
                assigned = True
                break
        if not assigned:
            round_slots.append(set(all_four))
            pairings.append(
                MatchPairing(
                    round_number=len(round_slots), team1=team1, team2=team2
                )
            )

    return pairings


# ---------------------------------------------------------------------------
# Public: fixed draw entry point
# ---------------------------------------------------------------------------


def generate_fixed_draw(player_ids: list[int]) -> list[MatchPairing]:
    """Generate all Vorrunde pairings upfront for a fixed draw tournament.

    Args:
        player_ids: List of player IDs participating in the tournament.
                    Length must be 9–13.

    Returns:
        Ordered list of MatchPairing objects (by round_number).

    Raises:
        ValueError: if player_count is out of range.
    """
    validate_player_count(len(player_ids))
    if is_doubles_mode(len(player_ids)):
        return _generate_doubles_fixed_draw(player_ids)
    return _generate_singles_fixed_draw(player_ids)


# ---------------------------------------------------------------------------
# Swiss system
# ---------------------------------------------------------------------------


@dataclass
class SwissState:
    """Mutable state for an ongoing Swiss tournament."""

    player_ids: list[int]
    standings: dict[int, PlayerStanding] = field(default_factory=dict)
    played_pairs: set[frozenset[int]] = field(default_factory=set)
    current_round: int = 0
    bye_counts: dict[int, int] = field(default_factory=dict)
    partner_history: dict[int, set[int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.standings:
            self.standings = {
                pid: PlayerStanding(player_id=pid) for pid in self.player_ids
            }
        if not self.bye_counts:
            self.bye_counts = {pid: 0 for pid in self.player_ids}
        if not self.partner_history:
            self.partner_history = {pid: set() for pid in self.player_ids}

    def _pair_key(self, a: int, b: int) -> frozenset[int]:
        return frozenset({a, b})

    def have_played(self, a: int, b: int) -> bool:
        return self._pair_key(a, b) in self.played_pairs

    def record_played(self, a: int, b: int) -> None:
        self.played_pairs.add(self._pair_key(a, b))


def _swiss_pair_singles(
    state: SwissState,
) -> list[MatchPairing]:
    """Pair players for one Swiss round in singles mode.

    When the player count is odd, the bye player is chosen proactively
    (before greedy pairing) to ensure fair bye rotation:
    - Primary:   fewest prior byes (so the same player is not skipped twice)
    - Secondary: lowest current ranking (weakest player sits out)

    The remaining even-sized pool is then paired greedily top-down.
    """
    sorted_players = sorted(
        state.player_ids,
        key=lambda pid: state.standings[pid].sort_key,
        reverse=True,
    )

    round_num = state.current_round  # already incremented by caller
    pairings: list[MatchPairing] = []
    used: set[int] = set()

    # With an odd number of players, proactively pick the bye player so
    # that the player who has already had the most byes is never chosen.
    if len(sorted_players) % 2 == 1:
        bye_player = min(
            sorted_players,
            key=lambda pid: (
                state.bye_counts.get(pid, 0),   # fewest byes = most eligible for bye
                state.standings[pid].sort_key,   # tiebreak: lowest ranked sits out
            ),
        )
        used.add(bye_player)
        state.bye_counts[bye_player] = state.bye_counts.get(bye_player, 0) + 1

    for pid in sorted_players:
        if pid in used:
            continue
        # Find best available opponent (closest in points, not yet played)
        for opp in sorted_players:
            if opp == pid or opp in used:
                continue
            if not state.have_played(pid, opp):
                pairings.append(
                    MatchPairing(round_number=round_num, team1=[pid], team2=[opp])
                )
                used.add(pid)
                used.add(opp)
                break

    return pairings


def _find_partner_pairs(
    players: list[int],
    partner_history: dict[int, set[int]],
) -> list[list[int]] | None:
    """Find a perfect partner matching with no repeat partnerships.

    Uses backtracking so it finds a valid solution whenever one exists,
    unlike a greedy approach that can reach dead-ends.

    Args:
        players:        Even-sized list of player IDs to be paired up.
        partner_history: Current partnership history (player → set of prior partners).

    Returns:
        List of [a, b] pairs forming a perfect matching, or None when no
        repeat-free matching is possible.
    """
    if not players:
        return []
    first = players[0]
    for i in range(1, len(players)):
        candidate = players[i]
        if candidate not in partner_history.get(first, set()):
            remaining = [players[j] for j in range(1, len(players)) if j != i]
            sub = _find_partner_pairs(remaining, partner_history)
            if sub is not None:
                return [[first, candidate]] + sub
    return None


def _swiss_pair_doubles(state: SwissState) -> list[MatchPairing]:
    """Pair players for one Swiss round in doubles mode.

    Three-step algorithm:

    Step 1 — Bye selection (only when n % 4 != 0, i.e. 10 players):
        Pick the n % 4 players with the fewest prior byes.  Tiebreak:
        lowest-ranked player sits out (weakest player is most eligible).
        Updates state.bye_counts for the chosen players.

    Step 2 — Partner assignment (no repeat partners):
        Uses backtracking to find a perfect matching where no two players
        who have previously been partners are paired again.  Updates
        state.partner_history.  Falls back to consecutive pairing only if
        all valid pairings are truly exhausted (shouldn't happen in practice
        with 10–12 players and ≤ 6 rounds).

    Step 3 — Opponent matching by team strength:
        Compute each team's combined strength (sum of individual sort_key
        primary values = reg_points + avg_bonus).  Sort teams descending and
        pair adjacent teams so the strongest team faces the 2nd strongest,
        3rd vs 4th, etc.
    """
    sorted_players = sorted(
        state.player_ids,
        key=lambda pid: state.standings[pid].sort_key,
        reverse=True,
    )

    round_num = state.current_round  # already incremented by caller
    n = len(sorted_players)
    num_byes = n % 4  # 0 for 12 players, 2 for 10 players

    active = list(sorted_players)

    # ------------------------------------------------------------------
    # Step 1: assign byes
    # ------------------------------------------------------------------
    if num_byes > 0:
        # Sort ascending: fewest byes first; tiebreak: lowest sort_key (weakest)
        bye_candidates = sorted(
            sorted_players,
            key=lambda pid: (
                state.bye_counts[pid],
                state.standings[pid].sort_key,
            ),
        )
        for pid in bye_candidates[:num_byes]:
            state.bye_counts[pid] += 1
            active.remove(pid)

    # ------------------------------------------------------------------
    # Step 2: find valid partner pairs via backtracking
    # Shuffle first so partners are assigned randomly, not by rank order.
    # Step 3 still ensures teams of similar strength face each other.
    # ------------------------------------------------------------------
    random.shuffle(active)
    partner_pairs = _find_partner_pairs(active, state.partner_history)
    if partner_pairs is None:
        # All valid pairings exhausted — pair consecutively as a last resort
        partner_pairs = [
            [active[i], active[i + 1]] for i in range(0, len(active) - 1, 2)
        ]

    for a, b in partner_pairs:
        state.partner_history[a].add(b)
        state.partner_history[b].add(a)

    # ------------------------------------------------------------------
    # Step 3: sort teams by combined strength, pair adjacent
    # ------------------------------------------------------------------
    def _team_strength(pair: list[int]) -> float:
        return sum(state.standings[pid].sort_key[0] for pid in pair)

    teams = sorted(partner_pairs, key=_team_strength, reverse=True)

    pairings: list[MatchPairing] = []
    for i in range(0, len(teams) - 1, 2):
        pairings.append(
            MatchPairing(
                round_number=round_num,
                team1=teams[i],
                team2=teams[i + 1],
            )
        )

    return pairings


def generate_swiss_round(state: SwissState) -> list[MatchPairing]:
    """Generate pairings for the next Swiss round.

    Call this after the previous round's results have been recorded via
    record_match_result().  Round 1 uses random pairings.

    Args:
        state: Current SwissState (mutated: current_round incremented,
               played_pairs updated).

    Returns:
        List of MatchPairing for the new round.
    """
    n = len(state.player_ids)
    validate_player_count(n)

    if state.current_round == 0:
        # Round 1: shuffle randomly
        shuffled = list(state.player_ids)
        random.shuffle(shuffled)
        state.player_ids = shuffled

    state.current_round += 1

    if is_doubles_mode(n):
        pairings = _swiss_pair_doubles(state)
    else:
        pairings = _swiss_pair_singles(state)

    # Record played pairs
    for p in pairings:
        if len(p.team1) == 1:
            state.record_played(p.team1[0], p.team2[0])
        else:
            # Doubles: track team-level pair as frozenset of all 4
            for a in p.team1:
                for b in p.team2:
                    state.record_played(a, b)

    return pairings


# ---------------------------------------------------------------------------
# Points calculation
# ---------------------------------------------------------------------------


def record_match_result(
    state: SwissState,
    pairing: MatchPairing,
    *,
    winner_team: int,  # 1 or 2
    scores: dict[int, int],   # player_id → dart points scored in this match
    visits: dict[int, int],   # player_id → number of visits thrown
    bonus_events: dict[int, list[DetectedEvent]] | None = None,
    # bonus_events: pass per-player event lists from the Vorrunde to have
    # update_standing_bonus() called automatically here.  When None (KO /
    # Lightning rounds, or callers that have not yet migrated) bonus_points
    # are left unchanged.  This is the preferred injection point so that
    # callers never have to call update_standing_bonus() separately.
) -> None:
    """Update standings after a completed match.

    Args:
        state: SwissState to update.
        pairing: The match that was played.
        winner_team: 1 if team1 won, 2 if team2 won.
        scores: Per-player dart points scored (used for individual average).
        visits: Per-player visit count.
        bonus_events: Optional per-player event lists (Vorrunde only).
            When provided, bonus_points are updated automatically via
            update_standing_bonus().
    """
    if winner_team not in {1, 2}:
        raise ValueError("winner_team must be 1 or 2.")

    all_players = pairing.team1 + pairing.team2
    missing = [pid for pid in all_players if pid not in scores or pid not in visits]
    if missing:
        raise ValueError(f"Missing score/visit data for player IDs: {missing}")

    winners = pairing.team1 if winner_team == 1 else pairing.team2
    losers = pairing.team2 if winner_team == 1 else pairing.team1

    for pid in winners:
        s = state.standings[pid]
        s.reg_points += 1.0
        s.total_score += scores[pid]
        s.total_visits += visits[pid]

    for pid in losers:
        s = state.standings[pid]
        # No reg_points for a loss
        s.total_score += scores[pid]
        s.total_visits += visits[pid]

    if bonus_events is not None:
        from app.services.bonus import update_standing_bonus  # avoid circular import

        for pid in all_players:
            if pid in bonus_events:
                update_standing_bonus(state.standings[pid], bonus_events[pid])


def get_standings(state: SwissState) -> list[PlayerStanding]:
    """Return standings sorted by (reg_points + avg_bonus) desc, bonus_points desc."""
    return sorted(
        state.standings.values(),
        key=lambda s: s.sort_key,
        reverse=True,
    )


# ---------------------------------------------------------------------------
# Persistence helpers (require an async DB session)
# ---------------------------------------------------------------------------


async def persist_standings(
    db: object,
    tournament_id: int,
    standings: dict[int, PlayerStanding],
) -> None:
    """Persist all in-memory PlayerStanding objects to TournamentPlayer rows.

    Args:
        db:            Async SQLAlchemy session (must be committed by caller).
        tournament_id: DB id of the tournament.
        standings:     Mapping player_id → PlayerStanding from SwissState.
    """
    from app.repositories.tournament_player_repo import (
        update_tournament_player_standing,
    )

    for player_id, standing in standings.items():
        await update_tournament_player_standing(
            db,
            tournament_id=tournament_id,
            player_id=player_id,
            reg_points=standing.reg_points,
            bonus_points=standing.bonus_points,
            avg_score=standing.avg_score,
        )
