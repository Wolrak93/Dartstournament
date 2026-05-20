"""KO bracket (knock-out phase) logic for the Backsberger Open.

Qualification rules:
- Top 6 players by (reg_points + avg_bonus) qualify via regular points.
  Tiebreak: higher bonus_points wins.
- The next 2 players with the highest bonus_points among those not yet
  qualified fill the remaining 2 spots.
- No player can qualify via both channels.

Bracket seeding: 1 vs 8, 2 vs 7, 3 vs 6, 4 vs 5.

Starting scores:
- Base score: 501 (Double-Out).
- Handicap applied when championship count difference >= 3.
  Stronger player's starting score += 100 + (diff - 3) * 40.

NOTE: The handicap computation here is intentionally inline.
      It will be replaced by a call to handicap.py once Task 7 is complete.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.vorrunde import PlayerStanding

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KO_BASE_SCORE: int = 501
KO_REGULAR_SPOTS: int = 6
KO_BONUS_SPOTS: int = 2
TOTAL_KO_SPOTS: int = KO_REGULAR_SPOTS + KO_BONUS_SPOTS  # 8

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class QualifiedPlayer:
    """One of the 8 KO-qualified players."""

    player_id: int
    seed: int  # 1–8
    reg_points: float  # reg_points + avg_bonus at time of qualification
    bonus_points: int
    championship_count: int
    qualified_via: str  # "regular" | "bonus"


@dataclass
class KOMatchup:
    """One match in the KO bracket, before DB insertion."""

    stage: str  # "qf" | "sf" | "final" | "third_place"
    match_index: int  # 0-based within the stage
    player1_id: int
    player2_id: int
    starting_score_p1: int  # handicap-adjusted
    starting_score_p2: int  # handicap-adjusted
    num_legs: int = 1  # final uses 2 legs


@dataclass
class KOBracket:
    """Snapshot of the full KO bracket at a given point in time.

    Created by generate_ko_bracket() with qf_matches populated.
    Evolved by advance_after_qf() and advance_after_sf().
    """

    seeding: list[QualifiedPlayer]  # 8 players, ordered seed 1 → 8
    qf_matches: list[KOMatchup]  # always 4 (generated at bracket creation)
    sf_matches: list[KOMatchup] = field(default_factory=list)  # 2, after QF
    final_match: KOMatchup | None = None
    third_place_match: KOMatchup | None = None
    lightning_player_ids: list[int] = field(default_factory=list)  # eliminated


# ---------------------------------------------------------------------------
# Handicap calculation (inline; to be replaced by Task 7 handicap.py)
# ---------------------------------------------------------------------------


def _compute_starting_scores(
    p1_championships: int,
    p2_championships: int,
    base_score: int = KO_BASE_SCORE,
) -> tuple[int, int]:
    """Return handicap-adjusted starting scores for two players.

    The stronger player (more championships) starts with extra points so they
    have more to score down.  Both players start at base_score when the
    difference is less than 3.

    Rules:
    - diff < 3:   no handicap — both start at base_score.
    - diff >= 3:  stronger side starts at base_score + 100 + (diff - 3) * 40.
                  (diff=3 → +100, diff=4 → +140, diff=5 → +180, …)

    TODO: Replace this with a call to handicap.py once Task 7 is complete.
    """
    diff = abs(p1_championships - p2_championships)
    if diff < 3:
        return base_score, base_score

    handicap = 100 + (diff - 3) * 40
    if p1_championships > p2_championships:
        return base_score + handicap, base_score
    return base_score, base_score + handicap


# ---------------------------------------------------------------------------
# Qualification
# ---------------------------------------------------------------------------


def qualify_players(
    standings: list[PlayerStanding],
    championship_counts: dict[int, int],
) -> list[QualifiedPlayer]:
    """Determine the 8 KO-qualified players from the Vorrunde standings.

    Args:
        standings: Final Vorrunde standings (PlayerStanding objects).
        championship_counts: player_id → number of tournament championships.

    Returns:
        List of 8 QualifiedPlayer objects ordered by seed (1–8).
        Seeds 1–6 qualified via regular points; seeds 7–8 via bonus points.

    Raises:
        ValueError: if fewer than 8 players are in the standings.
    """
    if len(standings) < TOTAL_KO_SPOTS:
        raise ValueError(
            f"Need at least {TOTAL_KO_SPOTS} players in standings, "
            f"got {len(standings)}."
        )

    # Sort by primary key (reg_points + avg_bonus) desc, then bonus_points desc
    sorted_all = sorted(standings, key=lambda s: s.sort_key, reverse=True)

    # Top 6 qualify via regular points
    regular_standings = sorted_all[:KO_REGULAR_SPOTS]
    regular_ids = {s.player_id for s in regular_standings}

    # From remaining players: sort by bonus_points desc, take top 2
    remaining = sorted_all[KO_REGULAR_SPOTS:]
    bonus_standings = sorted(
        remaining, key=lambda s: s.bonus_points, reverse=True
    )[:KO_BONUS_SPOTS]

    # Build result list: seeds 1–6 regular, 7–8 bonus
    qualified: list[QualifiedPlayer] = []

    for seed, standing in enumerate(regular_standings, start=1):
        qualified.append(
            QualifiedPlayer(
                player_id=standing.player_id,
                seed=seed,
                reg_points=standing.reg_points + standing.avg_bonus,
                bonus_points=standing.bonus_points,
                championship_count=championship_counts.get(standing.player_id, 0),
                qualified_via="regular",
            )
        )

    for seed, standing in enumerate(bonus_standings, start=KO_REGULAR_SPOTS + 1):
        # Guard: bonus qualifier must not already be a regular qualifier
        if standing.player_id in regular_ids:  # pragma: no cover
            continue
        qualified.append(
            QualifiedPlayer(
                player_id=standing.player_id,
                seed=seed,
                reg_points=standing.reg_points + standing.avg_bonus,
                bonus_points=standing.bonus_points,
                championship_count=championship_counts.get(standing.player_id, 0),
                qualified_via="bonus",
            )
        )

    return qualified


# ---------------------------------------------------------------------------
# Bracket creation
# ---------------------------------------------------------------------------


def _seed_qf_pairs(seeding: list[QualifiedPlayer]) -> list[tuple[int, int]]:
    """Return QF pairings as (player1_id, player2_id) tuples.

    Standard single-elimination seeding: 1v8, 2v7, 3v6, 4v5.
    seeding is ordered seed 1 → 8 (index 0 = seed 1, index 7 = seed 8).
    """
    if len(seeding) != TOTAL_KO_SPOTS:
        raise ValueError(
            f"Expected exactly {TOTAL_KO_SPOTS} seeded players, got {len(seeding)}."
        )
    return [
        (seeding[0].player_id, seeding[7].player_id),  # 1 vs 8
        (seeding[1].player_id, seeding[6].player_id),  # 2 vs 7
        (seeding[2].player_id, seeding[5].player_id),  # 3 vs 6
        (seeding[3].player_id, seeding[4].player_id),  # 4 vs 5
    ]


def generate_ko_bracket(
    standings: list[PlayerStanding],
    championship_counts: dict[int, int],
) -> KOBracket:
    """Create the initial KO bracket with 4 QF matches.

    Qualifies players, assigns seeds 1–8, and generates QF matchups with
    handicap-adjusted starting scores.  Call advance_after_qf() once all
    QF results are recorded.

    Args:
        standings: Final Vorrunde standings.
        championship_counts: player_id → championship count.

    Returns:
        KOBracket with seeding and qf_matches populated.
    """
    seeding = qualify_players(standings, championship_counts)
    qf_pairs = _seed_qf_pairs(seeding)
    champ_by_id = {q.player_id: q.championship_count for q in seeding}

    qf_matches: list[KOMatchup] = []
    for idx, (p1_id, p2_id) in enumerate(qf_pairs):
        s1, s2 = _compute_starting_scores(champ_by_id[p1_id], champ_by_id[p2_id])
        qf_matches.append(
            KOMatchup(
                stage="qf",
                match_index=idx,
                player1_id=p1_id,
                player2_id=p2_id,
                starting_score_p1=s1,
                starting_score_p2=s2,
            )
        )

    return KOBracket(seeding=seeding, qf_matches=qf_matches)


# ---------------------------------------------------------------------------
# Bracket progression
# ---------------------------------------------------------------------------


def _resolve_match(
    match: KOMatchup, results: dict[int, int]
) -> tuple[int, int]:
    """Return (winner_id, loser_id) for a match given a results dict.

    Raises:
        ValueError: if the result is missing or the winner is not a participant.
    """
    if match.match_index not in results:
        raise ValueError(
            f"{match.stage.upper()} match {match.match_index}: result is missing."
        )
    winner_id = results[match.match_index]
    if winner_id == match.player1_id:
        return winner_id, match.player2_id
    if winner_id == match.player2_id:
        return winner_id, match.player1_id
    raise ValueError(
        f"{match.stage.upper()} match {match.match_index}: "
        f"winner {winner_id} is not a participant "
        f"({match.player1_id} vs {match.player2_id})."
    )


def advance_after_qf(
    bracket: KOBracket,
    qf_results: dict[int, int],
    championship_counts: dict[int, int],
) -> KOBracket:
    """Advance the bracket after all QF results are known.

    QF winners proceed to the SF.  QF losers are eliminated and added to
    the Lightning Round pool.

    SF pairings follow the standard bracket: QF0 winner vs QF3 winner,
    QF1 winner vs QF2 winner (top half of the bracket meets bottom half).

    Args:
        bracket: The current KOBracket (with qf_matches populated).
        qf_results: match_index → winner player_id for each QF.
        championship_counts: player_id → championship count (for SF handicap).

    Returns:
        New KOBracket with sf_matches and lightning_player_ids updated.

    Raises:
        ValueError: if the bracket has the wrong number of QF matches or if
                    any result is missing / invalid.
    """
    if len(bracket.qf_matches) != 4:
        raise ValueError(
            f"Expected 4 QF matches, got {len(bracket.qf_matches)}."
        )

    sf_winners: list[int] = []
    lightning: list[int] = list(bracket.lightning_player_ids)

    for match in bracket.qf_matches:
        winner_id, loser_id = _resolve_match(match, qf_results)
        sf_winners.append(winner_id)
        lightning.append(loser_id)

    # Standard bracket: QF0 winner vs QF3 winner, QF1 winner vs QF2 winner
    sf_pairs = [
        (sf_winners[0], sf_winners[3]),
        (sf_winners[1], sf_winners[2]),
    ]

    sf_matches: list[KOMatchup] = []
    for idx, (p1_id, p2_id) in enumerate(sf_pairs):
        s1, s2 = _compute_starting_scores(
            championship_counts.get(p1_id, 0),
            championship_counts.get(p2_id, 0),
        )
        sf_matches.append(
            KOMatchup(
                stage="sf",
                match_index=idx,
                player1_id=p1_id,
                player2_id=p2_id,
                starting_score_p1=s1,
                starting_score_p2=s2,
            )
        )

    return KOBracket(
        seeding=bracket.seeding,
        qf_matches=bracket.qf_matches,
        sf_matches=sf_matches,
        lightning_player_ids=lightning,
    )


def advance_after_sf(
    bracket: KOBracket,
    sf_results: dict[int, int],
    championship_counts: dict[int, int],
) -> KOBracket:
    """Advance the bracket after all SF results are known.

    SF winners play the Final (2 legs).
    SF losers play the 3rd-place match.

    Args:
        bracket: The current KOBracket (with sf_matches populated).
        sf_results: match_index → winner player_id for each SF.
        championship_counts: player_id → championship count (for handicap).

    Returns:
        New KOBracket with final_match and third_place_match set.

    Raises:
        ValueError: if the bracket has the wrong number of SF matches or if
                    any result is missing / invalid.
    """
    if len(bracket.sf_matches) != 2:
        raise ValueError(
            f"Expected 2 SF matches, got {len(bracket.sf_matches)}."
        )

    finalists: list[int] = []
    third_place_players: list[int] = []

    for match in bracket.sf_matches:
        winner_id, loser_id = _resolve_match(match, sf_results)
        finalists.append(winner_id)
        third_place_players.append(loser_id)

    # Final — 2 legs
    f_s1, f_s2 = _compute_starting_scores(
        championship_counts.get(finalists[0], 0),
        championship_counts.get(finalists[1], 0),
    )
    final_match = KOMatchup(
        stage="final",
        match_index=0,
        player1_id=finalists[0],
        player2_id=finalists[1],
        starting_score_p1=f_s1,
        starting_score_p2=f_s2,
        num_legs=2,
    )

    # 3rd-place match
    tp_s1, tp_s2 = _compute_starting_scores(
        championship_counts.get(third_place_players[0], 0),
        championship_counts.get(third_place_players[1], 0),
    )
    third_place_match = KOMatchup(
        stage="third_place",
        match_index=0,
        player1_id=third_place_players[0],
        player2_id=third_place_players[1],
        starting_score_p1=tp_s1,
        starting_score_p2=tp_s2,
    )

    return KOBracket(
        seeding=bracket.seeding,
        qf_matches=bracket.qf_matches,
        sf_matches=bracket.sf_matches,
        final_match=final_match,
        third_place_match=third_place_match,
        lightning_player_ids=list(bracket.lightning_player_ids),
    )


# ---------------------------------------------------------------------------
# Persistence helpers (require an async DB session)
# ---------------------------------------------------------------------------


async def persist_ko_match_result(
    db: object,
    match_id: int,
    winner_id: int,
) -> object:
    """Record the winner of a KO match in the database.

    Args:
        db:        Async SQLAlchemy session (must be committed by caller).
        match_id:  DB id of the match that was played.
        winner_id: DB id of the winning player.

    Returns:
        The updated Match ORM object (flushed but not committed).
    """
    from app.repositories.match_repo import update_match_winner

    return await update_match_winner(db, match_id=match_id, winner_id=winner_id)


async def persist_ko_match_records(
    db: object,
    tournament_id: int,
    matchups: list[KOMatchup],
    round_number: int,
) -> list[object]:
    """Create Match DB records for a list of KO matchups.

    Args:
        db:            Async SQLAlchemy session (must be committed by caller).
        tournament_id: DB id of the tournament.
        matchups:      List of KOMatchup objects (from generate_ko_bracket etc.).
        round_number:  Round number to assign to all created matches.

    Returns:
        List of newly created Match ORM objects (flushed but not committed).
    """
    from app.models.match import RoundType
    from app.repositories.match_repo import create_match

    matches = []
    for i, mu in enumerate(matchups):
        match = await create_match(
            db,
            tournament_id=tournament_id,
            round_type=RoundType.ko,
            round_number=round_number,
            player1_id=mu.player1_id,
            player2_id=mu.player2_id,
            starting_score_p1=mu.starting_score_p1,
            starting_score_p2=mu.starting_score_p2,
        )
        matches.append(match)
    return matches
