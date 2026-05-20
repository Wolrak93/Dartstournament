"""Tests for the KO bracket logic (Task 4)."""

import pytest

from app.services.ko import (
    KO_BASE_SCORE,
    TOTAL_KO_SPOTS,
    KOBracket,
    _compute_starting_scores,
    advance_after_qf,
    advance_after_sf,
    generate_ko_bracket,
    qualify_players,
)
from app.services.vorrunde import PlayerStanding

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _standing(
    player_id: int,
    reg_points: float,
    bonus_points: int,
    total_score: int = 0,
    total_visits: int = 0,
) -> PlayerStanding:
    s = PlayerStanding(player_id=player_id)
    s.reg_points = reg_points
    s.bonus_points = bonus_points
    s.total_score = total_score
    s.total_visits = total_visits
    return s


def _make_standings(n: int) -> list[PlayerStanding]:
    """Create n players with descending reg_points (player 1 is best).

    Player pid: reg_points = n - pid + 1, bonus_points = (n - pid) * 10.
    """
    return [
        _standing(pid, reg_points=float(n - pid + 1), bonus_points=(n - pid) * 10)
        for pid in range(1, n + 1)
    ]


def _champs(player_ids: list[int], count: int = 0) -> dict[int, int]:
    return {pid: count for pid in player_ids}


def _all_players(n: int) -> list[int]:
    return list(range(1, n + 1))


# ---------------------------------------------------------------------------
# Qualification — basic
# ---------------------------------------------------------------------------


def test_qualify_13_players_exactly_8_qualify() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    result = qualify_players(standings, champ)
    assert len(result) == TOTAL_KO_SPOTS


def test_qualify_9_players_exactly_8_qualify() -> None:
    standings = _make_standings(9)
    champ = _champs(_all_players(9))
    result = qualify_players(standings, champ)
    assert len(result) == TOTAL_KO_SPOTS


def test_qualify_no_overlap() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    result = qualify_players(standings, champ)
    ids = [q.player_id for q in result]
    assert len(ids) == len(set(ids))


def test_qualify_top6_are_regular_qualifiers() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    result = qualify_players(standings, champ)
    regular = [q for q in result if q.qualified_via == "regular"]
    bonus = [q for q in result if q.qualified_via == "bonus"]
    assert len(regular) == 6
    assert len(bonus) == 2


def test_qualify_top6_by_reg_points() -> None:
    """Players 1–6 have the highest reg_points → they qualify via regular."""
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    result = qualify_players(standings, champ)
    regular_ids = {q.player_id for q in result if q.qualified_via == "regular"}
    assert regular_ids == {1, 2, 3, 4, 5, 6}


def test_qualify_bonus_from_remaining() -> None:
    """Players 7 and 8 have the most bonus points among non-qualified players."""
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    result = qualify_players(standings, champ)
    bonus_ids = {q.player_id for q in result if q.qualified_via == "bonus"}
    assert bonus_ids == {7, 8}


def test_qualify_seeds_assigned_correctly() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    result = qualify_players(standings, champ)
    seeds = [q.seed for q in result]
    assert seeds == list(range(1, TOTAL_KO_SPOTS + 1))


def test_qualify_too_few_players_raises() -> None:
    with pytest.raises(ValueError, match="at least"):
        qualify_players(_make_standings(7), {})


# ---------------------------------------------------------------------------
# Qualification — tiebreak
# ---------------------------------------------------------------------------


def test_qualify_tiebreak_reg_points() -> None:
    """Players 6 and 7 share the same reg_points; higher bonus_points wins
    the 6th regular spot, pushing the other into the bonus qualification."""
    standings = [
        _standing(1, 10.0, 100),
        _standing(2, 9.0, 90),
        _standing(3, 8.0, 80),
        _standing(4, 7.0, 70),
        _standing(5, 6.0, 60),
        _standing(6, 5.0, 50),  # same reg_points as player 7
        _standing(7, 5.0, 200),  # higher bonus → should take seed 6
        _standing(8, 4.0, 40),
        _standing(9, 3.0, 30),
    ]
    champ = _champs(_all_players(9))
    result = qualify_players(standings, champ)
    regular_ids = {q.player_id for q in result if q.qualified_via == "regular"}
    bonus_ids = {q.player_id for q in result if q.qualified_via == "bonus"}
    # Player 7 (higher bonus tiebreak) takes the 6th regular spot
    assert 7 in regular_ids
    assert 6 in bonus_ids


def test_qualify_tiebreak_preserves_total_of_8() -> None:
    """Tiebreak scenario still produces exactly 8 qualifiers."""
    standings = [
        _standing(
            pid,
            reg_points=5.0 if pid >= 5 else float(10 - pid),
            bonus_points=(10 - pid) * 5,
        )
        for pid in range(1, 12)
    ]
    champ = _champs(_all_players(11))
    result = qualify_players(standings, champ)
    assert len(result) == TOTAL_KO_SPOTS
    assert len({q.player_id for q in result}) == TOTAL_KO_SPOTS


# ---------------------------------------------------------------------------
# Bracket seeding
# ---------------------------------------------------------------------------


def test_bracket_seeding_1v8() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    m = bracket.qf_matches[0]
    # Seed 1 (player 1) vs seed 8 (player 8 — bonus qualifier)
    assert m.player1_id == 1
    assert m.player2_id == 8


def test_bracket_seeding_2v7() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    m = bracket.qf_matches[1]
    assert m.player1_id == 2
    assert m.player2_id == 7


def test_bracket_seeding_3v6() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    m = bracket.qf_matches[2]
    assert m.player1_id == 3
    assert m.player2_id == 6


def test_bracket_seeding_4v5() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    m = bracket.qf_matches[3]
    assert m.player1_id == 4
    assert m.player2_id == 5


def test_bracket_has_exactly_4_qf_matches() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    assert len(bracket.qf_matches) == 4


def test_bracket_stage_label_qf() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    for m in bracket.qf_matches:
        assert m.stage == "qf"


def test_bracket_qf_default_legs() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    for m in bracket.qf_matches:
        assert m.num_legs == 1


# ---------------------------------------------------------------------------
# advance_after_qf
# ---------------------------------------------------------------------------


def test_advance_qf_produces_2_sf_matches() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    results = {m.match_index: m.player1_id for m in bracket.qf_matches}
    updated = advance_after_qf(bracket, results, champ)
    assert len(updated.sf_matches) == 2


def test_advance_qf_winners_in_sf() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    results = {m.match_index: m.player1_id for m in bracket.qf_matches}
    updated = advance_after_qf(bracket, results, champ)
    sf_player_ids = (
        {updated.sf_matches[0].player1_id, updated.sf_matches[0].player2_id}
        | {updated.sf_matches[1].player1_id, updated.sf_matches[1].player2_id}
    )
    # player1 wins every QF match → seeds 1,2,3,4 go to SF
    assert sf_player_ids == {1, 2, 3, 4}


def test_advance_qf_losers_in_lightning() -> None:
    """QF losers must be added to the Lightning Round pool."""
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    # player1 wins each QF → losers are seeds 8, 7, 6, 5
    results = {m.match_index: m.player1_id for m in bracket.qf_matches}
    updated = advance_after_qf(bracket, results, champ)
    assert set(updated.lightning_player_ids) == {5, 6, 7, 8}


def test_advance_qf_exactly_4_lightning_players() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    results = {m.match_index: m.player1_id for m in bracket.qf_matches}
    updated = advance_after_qf(bracket, results, champ)
    assert len(updated.lightning_player_ids) == 4


def test_advance_qf_alternative_winner() -> None:
    """The lower seed can also win each match."""
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    results = {m.match_index: m.player2_id for m in bracket.qf_matches}
    updated = advance_after_qf(bracket, results, champ)
    # player2 wins each QF → seeds 8, 7, 6, 5 advance
    sf_ids = (
        {updated.sf_matches[0].player1_id, updated.sf_matches[0].player2_id}
        | {updated.sf_matches[1].player1_id, updated.sf_matches[1].player2_id}
    )
    assert sf_ids == {5, 6, 7, 8}
    assert set(updated.lightning_player_ids) == {1, 2, 3, 4}


def test_advance_qf_missing_result_raises() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    # Only provide 3 of 4 results
    results = {
        0: bracket.qf_matches[0].player1_id,
        1: bracket.qf_matches[1].player1_id,
        2: bracket.qf_matches[2].player1_id,
    }
    with pytest.raises(ValueError, match="missing"):
        advance_after_qf(bracket, results, champ)


def test_advance_qf_invalid_winner_raises() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    results = {
        0: 999,  # not a participant
        1: bracket.qf_matches[1].player1_id,
        2: bracket.qf_matches[2].player1_id,
        3: bracket.qf_matches[3].player1_id,
    }
    with pytest.raises(ValueError, match="not a participant"):
        advance_after_qf(bracket, results, champ)


def test_advance_qf_sf_stage_label() -> None:
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    results = {m.match_index: m.player1_id for m in bracket.qf_matches}
    updated = advance_after_qf(bracket, results, champ)
    for m in updated.sf_matches:
        assert m.stage == "sf"


def test_advance_qf_sf_bracket_structure() -> None:
    """SF pairings follow standard single-elimination: QF0 vs QF3, QF1 vs QF2."""
    standings = _make_standings(13)
    champ = _champs(_all_players(13))
    bracket = generate_ko_bracket(standings, champ)
    # seed 1 wins QF0, seed 2 wins QF1, seed 3 wins QF2, seed 4 wins QF3
    results = {m.match_index: m.player1_id for m in bracket.qf_matches}
    updated = advance_after_qf(bracket, results, champ)
    sf0_ids = {updated.sf_matches[0].player1_id, updated.sf_matches[0].player2_id}
    sf1_ids = {updated.sf_matches[1].player1_id, updated.sf_matches[1].player2_id}
    # SF0: QF0 winner (seed 1) vs QF3 winner (seed 4)
    assert sf0_ids == {1, 4}
    # SF1: QF1 winner (seed 2) vs QF2 winner (seed 3)
    assert sf1_ids == {2, 3}


# ---------------------------------------------------------------------------
# advance_after_sf
# ---------------------------------------------------------------------------


def _make_post_qf_bracket(n: int = 13) -> tuple[KOBracket, dict[int, int]]:
    """Create a bracket and advance it past QF with player1 winning each match."""
    standings = _make_standings(n)
    champ = _champs(_all_players(n))
    bracket = generate_ko_bracket(standings, champ)
    qf_results = {m.match_index: m.player1_id for m in bracket.qf_matches}
    updated = advance_after_qf(bracket, qf_results, champ)
    return updated, champ


def test_advance_sf_produces_final_and_third_place() -> None:
    bracket, champ = _make_post_qf_bracket()
    sf_results = {m.match_index: m.player1_id for m in bracket.sf_matches}
    final_bracket = advance_after_sf(bracket, sf_results, champ)
    assert final_bracket.final_match is not None
    assert final_bracket.third_place_match is not None


def test_advance_sf_finalists_are_sf_winners() -> None:
    bracket, champ = _make_post_qf_bracket()
    sf_results = {m.match_index: m.player1_id for m in bracket.sf_matches}
    final_bracket = advance_after_sf(bracket, sf_results, champ)
    fm = final_bracket.final_match
    assert fm is not None
    finalist_ids = {fm.player1_id, fm.player2_id}
    expected_winners = {m.player1_id for m in bracket.sf_matches}
    assert finalist_ids == expected_winners


def test_advance_sf_third_place_are_sf_losers() -> None:
    bracket, champ = _make_post_qf_bracket()
    sf_results = {m.match_index: m.player1_id for m in bracket.sf_matches}
    final_bracket = advance_after_sf(bracket, sf_results, champ)
    tp = final_bracket.third_place_match
    assert tp is not None
    third_ids = {tp.player1_id, tp.player2_id}
    expected_losers = {m.player2_id for m in bracket.sf_matches}
    assert third_ids == expected_losers


def test_advance_sf_finalists_and_third_place_disjoint() -> None:
    bracket, champ = _make_post_qf_bracket()
    sf_results = {m.match_index: m.player1_id for m in bracket.sf_matches}
    final_bracket = advance_after_sf(bracket, sf_results, champ)
    fm = final_bracket.final_match
    tp = final_bracket.third_place_match
    assert fm is not None
    assert tp is not None
    final_ids = {fm.player1_id, fm.player2_id}
    third_ids = {tp.player1_id, tp.player2_id}
    assert not (final_ids & third_ids)


def test_advance_sf_final_has_2_legs() -> None:
    bracket, champ = _make_post_qf_bracket()
    sf_results = {m.match_index: m.player1_id for m in bracket.sf_matches}
    final_bracket = advance_after_sf(bracket, sf_results, champ)
    assert final_bracket.final_match is not None
    assert final_bracket.final_match.num_legs == 2


def test_advance_sf_third_place_has_1_leg() -> None:
    bracket, champ = _make_post_qf_bracket()
    sf_results = {m.match_index: m.player1_id for m in bracket.sf_matches}
    final_bracket = advance_after_sf(bracket, sf_results, champ)
    assert final_bracket.third_place_match is not None
    assert final_bracket.third_place_match.num_legs == 1


def test_advance_sf_final_stage_label() -> None:
    bracket, champ = _make_post_qf_bracket()
    sf_results = {m.match_index: m.player1_id for m in bracket.sf_matches}
    final_bracket = advance_after_sf(bracket, sf_results, champ)
    assert final_bracket.final_match is not None
    assert final_bracket.final_match.stage == "final"
    assert final_bracket.third_place_match is not None
    assert final_bracket.third_place_match.stage == "third_place"


def test_advance_sf_lightning_unchanged() -> None:
    """SF losers go to 3rd-place match; the lightning pool must not change."""
    bracket, champ = _make_post_qf_bracket()
    lightning_before = list(bracket.lightning_player_ids)
    sf_results = {m.match_index: m.player1_id for m in bracket.sf_matches}
    final_bracket = advance_after_sf(bracket, sf_results, champ)
    assert final_bracket.lightning_player_ids == lightning_before


def test_advance_sf_missing_result_raises() -> None:
    bracket, champ = _make_post_qf_bracket()
    # Only one SF result provided
    sf_results = {0: bracket.sf_matches[0].player1_id}
    with pytest.raises(ValueError, match="missing"):
        advance_after_sf(bracket, sf_results, champ)


def test_advance_sf_invalid_winner_raises() -> None:
    bracket, champ = _make_post_qf_bracket()
    sf_results = {0: 999, 1: bracket.sf_matches[1].player1_id}
    with pytest.raises(ValueError, match="not a participant"):
        advance_after_sf(bracket, sf_results, champ)


# ---------------------------------------------------------------------------
# Handicap — _compute_starting_scores
# ---------------------------------------------------------------------------


def test_handicap_no_diff() -> None:
    s1, s2 = _compute_starting_scores(3, 3)
    assert s1 == KO_BASE_SCORE
    assert s2 == KO_BASE_SCORE


def test_handicap_diff_2_no_handicap() -> None:
    s1, s2 = _compute_starting_scores(4, 2)
    assert s1 == KO_BASE_SCORE
    assert s2 == KO_BASE_SCORE


def test_handicap_diff_3_stronger_is_p1() -> None:
    s1, s2 = _compute_starting_scores(5, 2)
    assert s1 == KO_BASE_SCORE + 100
    assert s2 == KO_BASE_SCORE


def test_handicap_diff_3_stronger_is_p2() -> None:
    s1, s2 = _compute_starting_scores(2, 5)
    assert s1 == KO_BASE_SCORE
    assert s2 == KO_BASE_SCORE + 100


def test_handicap_diff_4() -> None:
    s1, s2 = _compute_starting_scores(6, 2)
    assert s1 == KO_BASE_SCORE + 140
    assert s2 == KO_BASE_SCORE


def test_handicap_diff_5() -> None:
    # 100 + (5-3)*40 = 180
    s1, s2 = _compute_starting_scores(7, 2)
    assert s1 == KO_BASE_SCORE + 180
    assert s2 == KO_BASE_SCORE


def test_handicap_diff_1_boundary() -> None:
    s1, s2 = _compute_starting_scores(1, 0)
    assert s1 == KO_BASE_SCORE
    assert s2 == KO_BASE_SCORE


def test_handicap_zero_vs_zero() -> None:
    s1, s2 = _compute_starting_scores(0, 0)
    assert s1 == KO_BASE_SCORE
    assert s2 == KO_BASE_SCORE


def test_handicap_stored_in_qf_matches() -> None:
    """Player 1 with many championships triggers handicap in QF match 0."""
    standings = _make_standings(9)
    champ = {1: 10, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0}
    bracket = generate_ko_bracket(standings, champ)
    m = bracket.qf_matches[0]
    # Seed 1 = player 1 (10 champs) vs seed 8 = player 8 (0 champs)
    # diff = 10 → handicap = 100 + 7*40 = 380
    assert m.player1_id == 1
    assert m.starting_score_p1 == KO_BASE_SCORE + 380
    assert m.starting_score_p2 == KO_BASE_SCORE


def test_handicap_stored_in_sf_matches() -> None:
    """Handicap is also computed for SF matches (different championship counts)."""
    standings = _make_standings(13)
    # Give player 1 many championships — player 1 wins QF0 and should appear in SF
    champ: dict[int, int] = {pid: 0 for pid in range(1, 14)}
    champ[1] = 8  # diff vs opponent will be >= 3 after advancing

    bracket = generate_ko_bracket(standings, champ)
    qf_results = {m.match_index: m.player1_id for m in bracket.qf_matches}
    updated = advance_after_qf(bracket, qf_results, champ)

    # SF0: player1 vs player4 (player1 has 8 champs, player4 has 0 → diff=8)
    sf0 = updated.sf_matches[0]
    if sf0.player1_id == 1:
        expected_p1 = KO_BASE_SCORE + 100 + (8 - 3) * 40
        assert sf0.starting_score_p1 == expected_p1
        assert sf0.starting_score_p2 == KO_BASE_SCORE
    else:
        expected_p2 = KO_BASE_SCORE + 100 + (8 - 3) * 40
        assert sf0.starting_score_p1 == KO_BASE_SCORE
        assert sf0.starting_score_p2 == expected_p2
