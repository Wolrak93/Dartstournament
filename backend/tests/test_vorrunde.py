"""Tests for Vorrunde logic: pairing, points calculation, standings."""

from __future__ import annotations

import pytest

from app.services.events import DetectedEvent, EventType
from app.services.vorrunde import (
    MatchPairing,
    SwissState,
    generate_fixed_draw,
    generate_swiss_round,
    get_standings,
    is_doubles_mode,
    record_match_result,
    validate_player_count,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def player_ids(n: int) -> list[int]:
    return list(range(1, n + 1))


def match_appearances(pairings: list[MatchPairing]) -> dict[int, int]:
    """Count how many matches each player appears in."""
    counts: dict[int, int] = {}
    for p in pairings:
        for pid in p.team1 + p.team2:
            counts[pid] = counts.get(pid, 0) + 1
    return counts


def all_pairs_unique(pairings: list[MatchPairing]) -> bool:
    """Return True if no two singles matches share the same opponent pair."""
    seen: set[frozenset[int]] = set()
    for p in pairings:
        if len(p.team1) == 1:
            key = frozenset({p.team1[0], p.team2[0]})
            if key in seen:
                return False
            seen.add(key)
    return True


# ---------------------------------------------------------------------------
# Mode helpers
# ---------------------------------------------------------------------------


class TestModeHelpers:
    def test_doubles_mode_10(self):
        assert is_doubles_mode(10) is True

    def test_doubles_mode_12(self):
        assert is_doubles_mode(12) is True

    def test_singles_mode_9(self):
        assert is_doubles_mode(9) is False

    def test_singles_mode_11(self):
        assert is_doubles_mode(11) is False

    def test_singles_mode_13(self):
        assert is_doubles_mode(13) is False

    def test_validate_ok(self):
        for n in range(9, 14):
            validate_player_count(n)  # should not raise

    def test_validate_too_few(self):
        with pytest.raises(ValueError):
            validate_player_count(8)

    def test_validate_too_many(self):
        with pytest.raises(ValueError):
            validate_player_count(14)

    def test_validate_zero(self):
        with pytest.raises(ValueError):
            validate_player_count(0)


# ---------------------------------------------------------------------------
# Fixed draw — singles
# ---------------------------------------------------------------------------


class TestFixedDrawSingles:
    @pytest.mark.parametrize("n", [9, 11, 13])
    def test_no_repeat_pairings(self, n: int):
        pairings = generate_fixed_draw(player_ids(n))
        assert all_pairs_unique(pairings)

    @pytest.mark.parametrize("n", [9, 11, 13])
    def test_max_4_matches_per_player(self, n: int):
        pairings = generate_fixed_draw(player_ids(n))
        counts = match_appearances(pairings)
        for pid, count in counts.items():
            assert count <= 4, f"Player {pid} has {count} matches (max 4)"

    @pytest.mark.parametrize("n", [9, 11, 13])
    def test_most_players_get_matches(self, n: int):
        """All or all-but-one players should have at least 3 matches."""
        pairings = generate_fixed_draw(player_ids(n))
        counts = match_appearances(pairings)
        ids = player_ids(n)
        players_with_few = [pid for pid in ids if counts.get(pid, 0) < 3]
        # At most 1 player can have fewer than 3 (bye in odd-player schedule)
        assert len(players_with_few) <= 1

    @pytest.mark.parametrize("n", [9, 11, 13])
    def test_all_pairings_are_singles(self, n: int):
        pairings = generate_fixed_draw(player_ids(n))
        for p in pairings:
            assert len(p.team1) == 1
            assert len(p.team2) == 1

    @pytest.mark.parametrize("n", [9, 11, 13])
    def test_round_numbers_positive(self, n: int):
        pairings = generate_fixed_draw(player_ids(n))
        for p in pairings:
            assert p.round_number >= 1

    def test_invalid_player_count_raises(self):
        with pytest.raises(ValueError):
            generate_fixed_draw(player_ids(8))


# ---------------------------------------------------------------------------
# Fixed draw — doubles
# ---------------------------------------------------------------------------


class TestFixedDrawDoubles:
    @pytest.mark.parametrize("n", [10, 12])
    def test_6_matches_per_player(self, n: int):
        pairings = generate_fixed_draw(player_ids(n))
        counts = match_appearances(pairings)
        for pid in player_ids(n):
            assert counts.get(pid, 0) == 6, (
                f"Player {pid} has {counts.get(pid, 0)} matches, expected 6"
            )

    @pytest.mark.parametrize("n", [10, 12])
    def test_all_pairings_are_doubles(self, n: int):
        pairings = generate_fixed_draw(player_ids(n))
        for p in pairings:
            assert len(p.team1) == 2
            assert len(p.team2) == 2

    @pytest.mark.parametrize("n", [10, 12])
    def test_no_repeat_partners(self, n: int):
        pairings = generate_fixed_draw(player_ids(n))
        partner_history: dict[int, set[int]] = {}
        for p in pairings:
            for team in [p.team1, p.team2]:
                a, b = team[0], team[1]
                assert b not in partner_history.get(a, set()), (
                    f"Players {a} and {b} are partners more than once"
                )
                assert a not in partner_history.get(b, set()), (
                    f"Players {b} and {a} are partners more than once"
                )
                partner_history.setdefault(a, set()).add(b)
                partner_history.setdefault(b, set()).add(a)

    @pytest.mark.parametrize("n", [10, 12])
    def test_teams_have_4_unique_players(self, n: int):
        pairings = generate_fixed_draw(player_ids(n))
        for p in pairings:
            all_four = p.team1 + p.team2
            assert len(all_four) == len(set(all_four)), (
                "A player appears on both teams in the same match"
            )


# ---------------------------------------------------------------------------
# Swiss system — singles
# ---------------------------------------------------------------------------


class TestSwissSingles:
    @pytest.mark.parametrize("n", [9, 11, 13])
    def test_round1_random_pairings_cover_players(self, n: int):
        ids = player_ids(n)
        state = SwissState(player_ids=ids)
        pairings = generate_swiss_round(state)
        counts = match_appearances(pairings)
        # With odd n, at most 1 player gets a bye
        players_without_match = [pid for pid in ids if counts.get(pid, 0) == 0]
        assert len(players_without_match) <= 1

    @pytest.mark.parametrize("n", [9, 11, 13])
    def test_no_repeat_pairings_over_multiple_rounds(self, n: int):
        ids = player_ids(n)
        state = SwissState(player_ids=ids)

        all_pairings: list[MatchPairing] = []
        for _ in range(4):
            round_pairings = generate_swiss_round(state)
            all_pairings.extend(round_pairings)
            # Record dummy results so standings update
            for p in round_pairings:
                record_match_result(
                    state,
                    p,
                    winner_team=1,
                    scores={pid: 200 for pid in p.team1 + p.team2},
                    visits={pid: 10 for pid in p.team1 + p.team2},
                )

        assert all_pairs_unique(all_pairings), (
            "Repeat pairings detected in Swiss system"
        )

    def test_round_numbers_increment(self):
        state = SwissState(player_ids=player_ids(9))
        for expected_round in range(1, 4):
            pairings = generate_swiss_round(state)
            for p in pairings:
                assert p.round_number == expected_round
            for p in pairings:
                record_match_result(
                    state, p,
                    winner_team=1,
                    scores={pid: 200 for pid in p.team1 + p.team2},
                    visits={pid: 10 for pid in p.team1 + p.team2},
                )


# ---------------------------------------------------------------------------
# Swiss system — doubles
# ---------------------------------------------------------------------------


class TestSwissDoubles:
    def _run_rounds(self, state: SwissState, num_rounds: int) -> list[MatchPairing]:
        """Run num_rounds Swiss rounds with dummy results and return all pairings."""
        all_pairings: list[MatchPairing] = []
        for _ in range(num_rounds):
            round_pairings = generate_swiss_round(state)
            all_pairings.extend(round_pairings)
            for p in round_pairings:
                record_match_result(
                    state,
                    p,
                    winner_team=1,
                    scores={pid: 200 for pid in p.team1 + p.team2},
                    visits={pid: 10 for pid in p.team1 + p.team2},
                )
        return all_pairings

    @pytest.mark.parametrize("n", [10, 12])
    def test_all_pairings_are_doubles(self, n: int):
        state = SwissState(player_ids=player_ids(n))
        pairings = generate_swiss_round(state)
        for p in pairings:
            assert len(p.team1) == 2
            assert len(p.team2) == 2

    @pytest.mark.parametrize("n", [10, 12])
    def test_teams_have_4_unique_players(self, n: int):
        state = SwissState(player_ids=player_ids(n))
        pairings = generate_swiss_round(state)
        for p in pairings:
            all_four = p.team1 + p.team2
            assert len(all_four) == len(set(all_four)), (
                "A player appears on both teams in the same match"
            )

    @pytest.mark.parametrize("n", [10, 12])
    def test_no_repeat_partners_over_multiple_rounds(self, n: int):
        state = SwissState(player_ids=player_ids(n))
        all_pairings = self._run_rounds(state, 6)

        seen_partners: dict[int, set[int]] = {}
        for p in all_pairings:
            for team in [p.team1, p.team2]:
                a, b = team[0], team[1]
                assert b not in seen_partners.get(a, set()), (
                    f"Players {a} and {b} were partners more than once"
                )
                seen_partners.setdefault(a, set()).add(b)
                seen_partners.setdefault(b, set()).add(a)

    def test_no_byes_for_12_players(self):
        """With 12 players every player must participate in every round."""
        ids = player_ids(12)
        state = SwissState(player_ids=ids)
        for _ in range(6):
            round_pairings = generate_swiss_round(state)
            ids_in_round = {pid for p in round_pairings for pid in p.team1 + p.team2}
            assert ids_in_round == set(ids), "Not all 12 players participated in round"
            for p in round_pairings:
                record_match_result(
                    state,
                    p,
                    winner_team=1,
                    scores={pid: 200 for pid in p.team1 + p.team2},
                    visits={pid: 10 for pid in p.team1 + p.team2},
                )

    def test_bye_fairness_10_players(self):
        """With 10 players byes must be distributed as evenly as possible.

        Over 6 rounds, 12 byes total are handed out to 10 players.
        The fairest distribution is 8 players with 1 bye and 2 players
        with 2 byes → max − min ≤ 1.
        """
        state = SwissState(player_ids=player_ids(10))
        self._run_rounds(state, 6)
        bye_vals = list(state.bye_counts.values())
        assert max(bye_vals) - min(bye_vals) <= 1, (
            f"Bye counts are unfair: {bye_vals}"
        )

    def test_exactly_2_byes_per_round_for_10_players(self):
        """Each round with 10 players exactly 2 players must sit out."""
        state = SwissState(player_ids=player_ids(10))
        for _ in range(4):
            round_pairings = generate_swiss_round(state)
            ids_playing = {pid for p in round_pairings for pid in p.team1 + p.team2}
            assert len(ids_playing) == 8, (
                f"Expected 8 active players, got {len(ids_playing)}"
            )
            for p in round_pairings:
                record_match_result(
                    state,
                    p,
                    winner_team=1,
                    scores={pid: 200 for pid in p.team1 + p.team2},
                    visits={pid: 10 for pid in p.team1 + p.team2},
                )

    @pytest.mark.parametrize("n", [10, 12])
    def test_round_numbers_increment(self, n: int):
        state = SwissState(player_ids=player_ids(n))
        for expected_round in range(1, 4):
            pairings = generate_swiss_round(state)
            for p in pairings:
                assert p.round_number == expected_round
            for p in pairings:
                record_match_result(
                    state,
                    p,
                    winner_team=1,
                    scores={pid: 200 for pid in p.team1 + p.team2},
                    visits={pid: 10 for pid in p.team1 + p.team2},
                )

    def test_stronger_teams_face_each_other(self):
        """After a round where standings differ, team strength should be
        respected: the strongest team must face the 2nd-strongest team."""
        ids = player_ids(12)
        state = SwissState(player_ids=ids)

        # Manually set distinct standings so team strength is predictable
        for i, pid in enumerate(ids):
            state.standings[pid].reg_points = float(len(ids) - i)  # 12, 11, ..., 1

        pairings = generate_swiss_round(state)

        def team_strength(team: list[int]) -> float:
            return sum(state.standings[pid].reg_points for pid in team)

        match_strengths = [
            (team_strength(p.team1), team_strength(p.team2)) for p in pairings
        ]
        # The match with the highest total combined strength should be match 1
        combined = [s1 + s2 for s1, s2 in match_strengths]
        assert combined[0] == max(combined), (
            "The strongest teams are not paired against each other"
        )


# ---------------------------------------------------------------------------
# Points calculation
# ---------------------------------------------------------------------------


class TestPointsCalculation:
    def test_winner_gets_1_reg_point(self):
        state = SwissState(player_ids=[1, 2])
        pairing = MatchPairing(round_number=1, team1=[1], team2=[2])
        record_match_result(
            state, pairing,
            winner_team=1,
            scores={1: 301, 2: 250},
            visits={1: 15, 2: 18},
        )
        assert state.standings[1].reg_points == 1.0
        assert state.standings[2].reg_points == 0.0

    def test_average_calculated_correctly(self):
        state = SwissState(player_ids=[1, 2])
        pairing = MatchPairing(round_number=1, team1=[1], team2=[2])
        # Player 1: 240 points in 8 visits → average = 30.0
        record_match_result(
            state, pairing,
            winner_team=1,
            scores={1: 240, 2: 180},
            visits={1: 8, 2: 9},
        )
        assert state.standings[1].avg_score == pytest.approx(30.0)

    def test_avg_bonus_added_to_sort_key(self):
        """Average/100 should contribute to sort_key."""
        state = SwissState(player_ids=[1, 2])
        pairing = MatchPairing(round_number=1, team1=[1], team2=[2])
        # Player 1: avg = 100 → avg_bonus = 1.0; wins → reg_points=1
        # Player 2: avg = 50 → avg_bonus = 0.5; loses → reg_points=0
        record_match_result(
            state, pairing,
            winner_team=1,
            scores={1: 100, 2: 50},
            visits={1: 1, 2: 1},
        )
        s1 = state.standings[1]
        s2 = state.standings[2]
        assert s1.sort_key > s2.sort_key

    def test_zero_avg_when_no_visits(self):
        state = SwissState(player_ids=[1])
        assert state.standings[1].avg_score == 0.0
        assert state.standings[1].avg_bonus == 0.0

    def test_multiple_matches_accumulate(self):
        state = SwissState(player_ids=[1, 2, 3])
        # Match 1: 1 beats 2
        p1 = MatchPairing(round_number=1, team1=[1], team2=[2])
        record_match_result(state, p1, winner_team=1,
                            scores={1: 200, 2: 150},
                            visits={1: 10, 2: 12})
        # Match 2: 1 beats 3
        p2 = MatchPairing(round_number=2, team1=[1], team2=[3])
        record_match_result(state, p2, winner_team=1,
                            scores={1: 180, 3: 160},
                            visits={1: 9, 3: 11})
        assert state.standings[1].reg_points == 2.0
        assert state.standings[1].total_visits == 19

    def test_doubles_individual_averages(self):
        """In doubles each player's own score/visits are tracked independently."""
        state = SwissState(player_ids=[1, 2, 3, 4])
        pairing = MatchPairing(round_number=1, team1=[1, 2], team2=[3, 4])
        # Player 1 throws well (avg 60), player 2 throws badly (avg 20);
        # team won, so both get reg_points.
        record_match_result(
            state, pairing,
            winner_team=1,
            scores={1: 300, 2: 100, 3: 200, 4: 180},
            visits={1: 5,   2: 5,   3: 5,   4: 5},
        )
        assert state.standings[1].avg_score == pytest.approx(60.0)
        assert state.standings[2].avg_score == pytest.approx(20.0)
        assert state.standings[3].avg_score == pytest.approx(40.0)
        assert state.standings[4].avg_score == pytest.approx(36.0)
        # Both winners get 1 reg_point
        assert state.standings[1].reg_points == 1.0
        assert state.standings[2].reg_points == 1.0
        # Both losers get 0
        assert state.standings[3].reg_points == 0.0
        assert state.standings[4].reg_points == 0.0

    def test_missing_player_data_raises(self):
        """ValueError if scores/visits dict is missing a player from the match."""
        state = SwissState(player_ids=[1, 2])
        pairing = MatchPairing(round_number=1, team1=[1], team2=[2])
        with pytest.raises(ValueError, match="Missing score"):
            record_match_result(
                state, pairing,
                winner_team=1,
                scores={1: 200},   # player 2 missing
                visits={1: 10, 2: 12},
            )


# ---------------------------------------------------------------------------
# Standings ordering
# ---------------------------------------------------------------------------


class TestStandingsOrdering:
    def test_winner_ranks_above_loser(self):
        state = SwissState(player_ids=[1, 2])
        pairing = MatchPairing(round_number=1, team1=[1], team2=[2])
        record_match_result(state, pairing, winner_team=1,
                            scores={1: 200, 2: 150},
                            visits={1: 10, 2: 12})
        standings = get_standings(state)
        assert standings[0].player_id == 1

    def test_tied_reg_points_tiebreak_by_bonus(self):
        """When two players have equal reg_points, higher bonus_points wins."""
        state = SwissState(player_ids=[1, 2])
        state.standings[1].reg_points = 2.0
        state.standings[2].reg_points = 2.0
        state.standings[1].bonus_points = 50
        state.standings[2].bonus_points = 100
        # Both have 0 visits → avg_bonus = 0 for both
        standings = get_standings(state)
        assert standings[0].player_id == 2  # higher bonus_points

    def test_standings_sorted_descending(self):
        state = SwissState(player_ids=[1, 2, 3, 4])
        state.standings[1].reg_points = 3.0
        state.standings[2].reg_points = 1.0
        state.standings[3].reg_points = 2.0
        state.standings[4].reg_points = 0.0
        standings = get_standings(state)
        points = [s.reg_points for s in standings]
        assert points == sorted(points, reverse=True)

    def test_avg_bonus_breaks_tie_over_plain_reg_points(self):
        """Player with same wins but higher average ranks higher."""
        state = SwissState(player_ids=[1, 2])
        state.standings[1].reg_points = 1.0
        state.standings[2].reg_points = 1.0
        state.standings[1].total_score = 200
        state.standings[1].total_visits = 10  # avg=20, bonus=0.2
        state.standings[2].total_score = 100
        state.standings[2].total_visits = 10  # avg=10, bonus=0.1
        standings = get_standings(state)
        assert standings[0].player_id == 1


# ---------------------------------------------------------------------------
# Regression: bonus_points updated automatically via record_match_result()
# ---------------------------------------------------------------------------


class TestBonusPointsWiring:
    """Verify that bonus_events passed to record_match_result() are applied."""

    def _make_pairing(self) -> MatchPairing:
        return MatchPairing(round_number=1, team1=[1], team2=[2])

    def test_bonus_events_update_winner_bonus_points(self):
        state = SwissState(player_ids=[1, 2])
        pairing = self._make_pairing()
        ev26 = DetectedEvent(event_type=EventType.GEWORFEN_26, count=1, bonus_value=26)
        bonus_events = {1: [ev26], 2: []}
        record_match_result(
            state,
            pairing,
            winner_team=1,
            scores={1: 100, 2: 80},
            visits={1: 5, 2: 6},
            bonus_events=bonus_events,
        )
        assert state.standings[1].bonus_points == 26
        assert state.standings[2].bonus_points == 0

    def test_bonus_events_update_loser_bonus_points(self):
        state = SwissState(player_ids=[1, 2])
        pairing = self._make_pairing()
        ev180 = DetectedEvent(
            event_type=EventType.GEWORFEN_180, count=1, bonus_value=1800
        )
        bonus_events = {1: [], 2: [ev180]}
        record_match_result(
            state,
            pairing,
            winner_team=1,
            scores={1: 100, 2: 80},
            visits={1: 5, 2: 6},
            bonus_events=bonus_events,
        )
        assert state.standings[1].bonus_points == 0
        assert state.standings[2].bonus_points == 1800

    def test_no_bonus_events_leaves_bonus_points_unchanged(self):
        """Without bonus_events the existing bonus_points must be preserved."""
        state = SwissState(player_ids=[1, 2])
        state.standings[1].bonus_points = 42
        pairing = self._make_pairing()
        record_match_result(
            state,
            pairing,
            winner_team=1,
            scores={1: 100, 2: 80},
            visits={1: 5, 2: 6},
        )
        assert state.standings[1].bonus_points == 42
        assert state.standings[2].bonus_points == 0

    def test_negative_bonus_events_reduce_points(self):
        state = SwissState(player_ids=[1, 2])
        pairing = self._make_pairing()
        bonus_events = {
            1: [DetectedEvent(event_type=EventType.BUST, count=2, bonus_value=-2)],
            2: [],
        }
        record_match_result(
            state,
            pairing,
            winner_team=1,
            scores={1: 100, 2: 80},
            visits={1: 5, 2: 6},
            bonus_events=bonus_events,
        )
        assert state.standings[1].bonus_points == -2
