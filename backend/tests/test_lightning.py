"""Tests for the Lightning Round (Nebenrunde) scheduling logic."""

import pytest

from app.services.lightning import (
    LIGHTNING_BASE_SCORE,
    add_eliminated_players,
    create_lightning_state,
    generate_lightning_round,
    get_lightning_standings,
    record_lightning_result,
)

# ---------------------------------------------------------------------------
# create_lightning_state
# ---------------------------------------------------------------------------


def test_create_lightning_state_empty():
    state = create_lightning_state([])
    assert state.pending_pool == []
    assert state.standings == {}
    assert state.rounds == []


def test_create_lightning_state_with_non_qualifiers():
    state = create_lightning_state([10, 11, 12])
    assert state.pending_pool == [10, 11, 12]
    assert set(state.standings.keys()) == {10, 11, 12}
    for pid, standing in state.standings.items():
        assert standing.player_id == pid
        assert standing.wins == 0
        assert standing.losses == 0


def test_create_lightning_state_deduplicates():
    state = create_lightning_state([5, 5, 6])
    assert state.pending_pool == [5, 6]


# ---------------------------------------------------------------------------
# add_eliminated_players
# ---------------------------------------------------------------------------


def test_add_eliminated_players_basic():
    state = create_lightning_state([100])
    state = add_eliminated_players(state, [1, 2, 3, 4])
    assert state.pending_pool == [100, 1, 2, 3, 4]
    assert set(state.standings.keys()) == {100, 1, 2, 3, 4}


def test_add_eliminated_players_deduplicates():
    state = create_lightning_state([1, 2])
    state = add_eliminated_players(state, [2, 3])
    assert state.pending_pool == [1, 2, 3]


def test_add_eliminated_players_does_not_mutate_original():
    state = create_lightning_state([1])
    _ = add_eliminated_players(state, [2])
    assert state.pending_pool == [1]


# ---------------------------------------------------------------------------
# generate_lightning_round — pairing and bye logic
# ---------------------------------------------------------------------------


def test_generate_round_empty_pool_is_noop():
    state = create_lightning_state([])
    state = generate_lightning_round(state)
    assert state.rounds == []
    assert state.next_round_number == 1


def test_generate_round_two_players():
    state = create_lightning_state([1, 2])
    state = generate_lightning_round(state)

    assert len(state.rounds) == 1
    r = state.rounds[0]
    assert r.round_number == 1
    assert len(r.matches) == 1
    assert r.bye_player_id is None
    assert r.matches[0].player1_id == 1
    assert r.matches[0].player2_id == 2
    assert state.pending_pool == []


def test_generate_round_four_players():
    state = create_lightning_state([1, 2, 3, 4])
    state = generate_lightning_round(state)

    r = state.rounds[0]
    assert len(r.matches) == 2
    assert r.bye_player_id is None
    assert state.pending_pool == []


def test_generate_round_starting_score_is_301():
    state = create_lightning_state([1, 2])
    state = generate_lightning_round(state)
    assert state.rounds[0].matches[0].starting_score == LIGHTNING_BASE_SCORE


def test_five_players_pairing_with_bye():
    """Required test: 5 eliminated players → 2 matches + 1 bye."""
    state = create_lightning_state([1, 2, 3, 4, 5])
    state = generate_lightning_round(state)

    assert len(state.rounds) == 1
    r = state.rounds[0]
    assert len(r.matches) == 2
    assert r.bye_player_id is not None

    # Bye player must have been the last in the pool (player 5)
    assert r.bye_player_id == 5

    # Bye player stays in pool for next round
    assert state.pending_pool == [5]

    # Matches cover the other 4 players
    all_matched = {m.player1_id for m in r.matches} | {m.player2_id for m in r.matches}
    assert all_matched == {1, 2, 3, 4}


def test_odd_pool_bye_carries_over():
    """Bye player from one round carries into the next."""
    state = create_lightning_state([1, 2, 3])  # odd
    state = generate_lightning_round(state)

    assert state.rounds[0].bye_player_id == 3
    assert state.pending_pool == [3]

    # Next round: bye player + 2 new
    state = add_eliminated_players(state, [4, 5])
    state = generate_lightning_round(state)

    r2 = state.rounds[1]
    assert r2.round_number == 2
    assert len(r2.matches) == 1  # 3 players (3, 4, 5) → 1 match + 1 bye
    assert r2.bye_player_id is not None
    assert len(state.pending_pool) == 1


def test_generate_round_increments_round_number():
    state = create_lightning_state([1, 2, 3, 4])
    state = generate_lightning_round(state)
    state = add_eliminated_players(state, [5, 6])
    state = generate_lightning_round(state)

    assert state.rounds[0].round_number == 1
    assert state.rounds[1].round_number == 2


# ---------------------------------------------------------------------------
# Lightning schedule across 3 KO rounds (required test)
# ---------------------------------------------------------------------------


def test_lightning_schedule_across_3_ko_rounds():
    """Full schedule simulation across 3 KO elimination waves."""
    # Initial: 1 non-qualifier
    state = create_lightning_state([100])

    # KO Round 1 (QF): 4 eliminated
    state = add_eliminated_players(state, [1, 2, 3, 4])
    assert len(state.pending_pool) == 5  # 100 + 1,2,3,4

    state = generate_lightning_round(state)  # Lightning Round 1

    r1 = state.rounds[0]
    assert r1.round_number == 1
    assert len(r1.matches) == 2  # 5 players → 2 matches + 1 bye
    assert r1.bye_player_id is not None
    assert len(state.pending_pool) == 1  # bye player remains

    # KO Round 2 (SF): 2 more eliminated
    state = add_eliminated_players(state, [5, 6])
    # pool = [bye_player, 5, 6] = 3 players → odd

    state = generate_lightning_round(state)  # Lightning Round 2

    r2 = state.rounds[1]
    assert r2.round_number == 2
    assert len(r2.matches) == 1  # 3 players → 1 match + 1 bye
    assert r2.bye_player_id is not None
    assert len(state.pending_pool) == 1

    # KO Round 3: 1 more eliminated → even pool (bye + 1 new)
    state = add_eliminated_players(state, [7])
    # pool = [bye_player, 7] = 2 players → even

    state = generate_lightning_round(state)  # Lightning Round 3

    r3 = state.rounds[2]
    assert r3.round_number == 3
    assert len(r3.matches) == 1
    assert r3.bye_player_id is None
    assert state.pending_pool == []

    # All 3 rounds are tracked
    assert len(state.rounds) == 3


# ---------------------------------------------------------------------------
# record_lightning_result
# ---------------------------------------------------------------------------


def test_record_result_updates_standings():
    state = create_lightning_state([1, 2])
    state = generate_lightning_round(state)
    state = record_lightning_result(state, round_number=1, match_index=0, winner_id=1)

    assert state.standings[1].wins == 1
    assert state.standings[1].losses == 0
    assert state.standings[1].matches_played == 1

    assert state.standings[2].wins == 0
    assert state.standings[2].losses == 1
    assert state.standings[2].matches_played == 1


def test_record_result_player2_wins():
    state = create_lightning_state([1, 2])
    state = generate_lightning_round(state)
    state = record_lightning_result(state, round_number=1, match_index=0, winner_id=2)

    assert state.standings[2].wins == 1
    assert state.standings[1].losses == 1


def test_record_result_invalid_round_raises():
    state = create_lightning_state([1, 2])
    state = generate_lightning_round(state)
    with pytest.raises(ValueError, match="round 99 not found"):
        record_lightning_result(state, round_number=99, match_index=0, winner_id=1)


def test_record_result_invalid_match_index_raises():
    state = create_lightning_state([1, 2])
    state = generate_lightning_round(state)
    with pytest.raises(ValueError, match="out of range"):
        record_lightning_result(state, round_number=1, match_index=5, winner_id=1)


def test_record_result_invalid_winner_raises():
    state = create_lightning_state([1, 2])
    state = generate_lightning_round(state)
    with pytest.raises(ValueError, match="not a participant"):
        record_lightning_result(state, round_number=1, match_index=0, winner_id=99)


def test_record_result_does_not_mutate_original():
    state = create_lightning_state([1, 2])
    state = generate_lightning_round(state)
    new_state = record_lightning_result(
        state, round_number=1, match_index=0, winner_id=1
    )
    assert state.standings[1].wins == 0  # original unchanged
    assert new_state.standings[1].wins == 1


def test_cumulative_standings_across_multiple_rounds():
    state = create_lightning_state([1, 2, 3, 4])
    state = generate_lightning_round(state)
    state = record_lightning_result(state, 1, 0, winner_id=1)
    state = record_lightning_result(state, 1, 1, winner_id=3)

    state = add_eliminated_players(state, [5, 6])
    state = generate_lightning_round(state)
    state = record_lightning_result(state, 2, 0, winner_id=5)

    assert state.standings[1].wins == 1
    assert state.standings[3].wins == 1
    assert state.standings[5].wins == 1
    assert state.standings[2].losses == 1
    assert state.standings[4].losses == 1
    assert state.standings[6].losses == 1


# ---------------------------------------------------------------------------
# get_lightning_standings
# ---------------------------------------------------------------------------


def test_standings_sorted_by_wins():
    state = create_lightning_state([1, 2, 3, 4])
    state = generate_lightning_round(state)
    state = record_lightning_result(state, 1, 0, winner_id=1)
    state = record_lightning_result(state, 1, 1, winner_id=3)

    standings = get_lightning_standings(state)
    # Both winners have 1 win; losers have 0
    wins = [s.wins for s in standings]
    assert wins == sorted(wins, reverse=True)
    assert standings[0].wins >= standings[-1].wins
