"""Lightning Round (Nebenrunde) scheduling logic for the Backsberger Open.

Rules:
- Non-KO-qualifiers and players eliminated during the KO phase enter the pool.
- After each KO round, all pending pool players are paired for Lightning matches.
  If the pool count is odd, the last player receives a bye and stays in the pool
  for the next Lightning round.
- Format: 301 points, Single-Out (no Double-Out required).
- Standings track wins and losses across all Lightning rounds.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LIGHTNING_BASE_SCORE: int = 301

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class LightningMatchup:
    """One match in the Lightning Round."""

    round_number: int
    match_index: int  # 0-based within the round
    player1_id: int
    player2_id: int
    starting_score: int = field(default=LIGHTNING_BASE_SCORE)


@dataclass
class LightningRound:
    """One round of Lightning matches, generated after a KO stage."""

    round_number: int
    matches: list[LightningMatchup]
    bye_player_id: int | None = None  # player who gets a bye this round


@dataclass
class LightningStanding:
    """Accumulated record for one player in the Lightning Round."""

    player_id: int
    wins: int = 0
    losses: int = 0
    matches_played: int = 0


@dataclass
class LightningState:
    """Full Lightning Round state: pool, rounds played, and standings."""

    rounds: list[LightningRound] = field(default_factory=list)
    pending_pool: list[int] = field(default_factory=list)
    standings: dict[int, LightningStanding] = field(default_factory=dict)
    next_round_number: int = 1


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------


def create_lightning_state(non_qualifier_ids: list[int]) -> LightningState:
    """Create the initial Lightning state for Vorrunde non-qualifiers.

    Args:
        non_qualifier_ids: Player IDs of players who did not qualify for KO.

    Returns:
        Fresh LightningState with the non-qualifiers ready in the pool.
    """
    state = LightningState()
    for pid in non_qualifier_ids:
        if pid not in state.pending_pool:
            state.pending_pool.append(pid)
        state.standings[pid] = LightningStanding(player_id=pid)
    return state


def add_eliminated_players(
    state: LightningState,
    player_ids: list[int],
) -> LightningState:
    """Add newly eliminated KO players to the pending pool.

    Duplicate IDs are silently ignored.

    Args:
        state:      Current Lightning state.
        player_ids: Player IDs of players just eliminated from KO.

    Returns:
        New LightningState with the eliminated players appended to the pool.
    """
    new_state = deepcopy(state)
    for pid in player_ids:
        if pid not in new_state.pending_pool:
            new_state.pending_pool.append(pid)
        if pid not in new_state.standings:
            new_state.standings[pid] = LightningStanding(player_id=pid)
    return new_state


def generate_lightning_round(state: LightningState) -> LightningState:
    """Generate the next Lightning Round from the current pending pool.

    All pending players are paired sequentially (first with second, third with
    fourth, …).  If the pool has an odd count, the last player receives a bye
    and remains in the pool for the next round.

    Does nothing (returns state unchanged) if the pool is empty.

    Args:
        state: Current Lightning state.

    Returns:
        New LightningState with the new round appended and the pool updated
        (only the bye player, if any, remains).
    """
    new_state = deepcopy(state)

    pool = list(new_state.pending_pool)
    if not pool:
        return new_state

    round_num = new_state.next_round_number
    new_state.next_round_number += 1

    bye_player: int | None = None
    if len(pool) % 2 == 1:
        bye_player = pool.pop()  # last player gets the bye

    matches: list[LightningMatchup] = []
    for i in range(0, len(pool), 2):
        matches.append(
            LightningMatchup(
                round_number=round_num,
                match_index=len(matches),
                player1_id=pool[i],
                player2_id=pool[i + 1],
            )
        )

    new_state.pending_pool = [bye_player] if bye_player is not None else []
    new_state.rounds.append(
        LightningRound(
            round_number=round_num,
            matches=matches,
            bye_player_id=bye_player,
        )
    )
    return new_state


def record_lightning_result(
    state: LightningState,
    round_number: int,
    match_index: int,
    winner_id: int,
) -> LightningState:
    """Record the result of a Lightning match and update standings.

    Args:
        state:        Current Lightning state.
        round_number: The round number of the finished match.
        match_index:  0-based index of the match within the round.
        winner_id:    player_id of the winner.

    Returns:
        New LightningState with updated standings.

    Raises:
        ValueError: if the round or match is not found, or if winner_id is not
                    a participant of the specified match.
    """
    new_state = deepcopy(state)

    target_round: LightningRound | None = None
    for r in new_state.rounds:
        if r.round_number == round_number:
            target_round = r
            break

    if target_round is None:
        raise ValueError(f"Lightning round {round_number} not found.")

    if match_index < 0 or match_index >= len(target_round.matches):
        raise ValueError(
            f"Match index {match_index} out of range for round {round_number} "
            f"(has {len(target_round.matches)} matches)."
        )

    match = target_round.matches[match_index]
    if winner_id == match.player1_id:
        loser_id = match.player2_id
    elif winner_id == match.player2_id:
        loser_id = match.player1_id
    else:
        raise ValueError(
            f"Winner {winner_id} is not a participant in "
            f"round {round_number} match {match_index} "
            f"({match.player1_id} vs {match.player2_id})."
        )

    winner_standing = new_state.standings.setdefault(
        winner_id, LightningStanding(player_id=winner_id)
    )
    winner_standing.wins += 1
    winner_standing.matches_played += 1

    loser_standing = new_state.standings.setdefault(
        loser_id, LightningStanding(player_id=loser_id)
    )
    loser_standing.losses += 1
    loser_standing.matches_played += 1

    return new_state


def get_lightning_standings(state: LightningState) -> list[LightningStanding]:
    """Return Lightning standings sorted by wins descending.

    Args:
        state: Current Lightning state.

    Returns:
        List of LightningStanding objects ordered by wins (desc).
    """
    return sorted(state.standings.values(), key=lambda s: s.wins, reverse=True)


# ---------------------------------------------------------------------------
# Persistence helpers (require an async DB session)
# ---------------------------------------------------------------------------


async def persist_lightning_match_result(
    db: object,
    match_id: int,
    winner_id: int,
) -> object:
    """Record the winner of a Lightning Round match in the database.

    Args:
        db:        Async SQLAlchemy session (must be committed by caller).
        match_id:  DB id of the match that was played.
        winner_id: DB id of the winning player.

    Returns:
        The updated Match ORM object (flushed but not committed).
    """
    from app.repositories.match_repo import update_match_winner

    return await update_match_winner(db, match_id=match_id, winner_id=winner_id)


async def persist_lightning_match_records(
    db: object,
    tournament_id: int,
    matchups: list[LightningMatchup],
) -> list[object]:
    """Create Match DB records for a Lightning Round.

    Args:
        db:            Async SQLAlchemy session (must be committed by caller).
        tournament_id: DB id of the tournament.
        matchups:      LightningMatchup objects from generate_next_round().

    Returns:
        List of newly created Match ORM objects (flushed but not committed).
    """
    from app.models.match import RoundType
    from app.repositories.match_repo import create_match

    matches = []
    for mu in matchups:
        match = await create_match(
            db,
            tournament_id=tournament_id,
            round_type=RoundType.lightning,
            round_number=mu.round_number,
            player1_id=mu.player1_id,
            player2_id=mu.player2_id,
            starting_score_p1=mu.starting_score,
            starting_score_p2=mu.starting_score,
        )
        matches.append(match)
    return matches
