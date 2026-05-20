"""Tests for the Match Flow Engine (Task 6)."""

from __future__ import annotations

import pytest
from conftest import _miss  # shared helper; defined once in conftest.py

from app.services.match import (
    CheckoutSuggestion,
    Dart,
    DartBand,
    VisitResult,
    dart_from_score,
    get_checkout_suggestion,
    process_visit,
    record_doubles_bull_throw,
    record_singles_bull_throw,
    should_switch_to_single_out,
    validate_dart,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _d(score: int, band: DartBand | None = None, number: int = 0) -> Dart:
    """Shorthand to build a Dart. If band is None, infers via dart_from_score."""
    if band is None:
        return dart_from_score(score)
    return Dart(score=score, band=band, number=number)


def _single(n: int) -> Dart:
    return Dart(score=n, band=DartBand.SINGLE, number=n)


def _double(n: int) -> Dart:
    return Dart(score=n * 2, band=DartBand.DOUBLE, number=n)


def _triple(n: int) -> Dart:
    return Dart(score=n * 3, band=DartBand.TRIPLE, number=n)


def _bull() -> Dart:
    return Dart(score=25, band=DartBand.BULL, number=25)


def _bullseye() -> Dart:
    return Dart(score=50, band=DartBand.BULLSEYE, number=25)


def _visit(
    d1: Dart, d2: Dart, d3: Dart, remaining: int, single_out: bool = False
) -> VisitResult:
    return process_visit(
        [d1, d2, d3], remaining, visit_number=1, single_out_mode=single_out
    )


# ---------------------------------------------------------------------------
# Bull throw tests
# ---------------------------------------------------------------------------


class TestBullThrow:
    # --- Singles ---

    def test_singles_player1_wins(self) -> None:
        result = record_singles_bull_throw(
            player1_id=1, player2_id=2, winner_id=1
        )
        assert result.play_order == [1, 2]

    def test_singles_player2_wins(self) -> None:
        result = record_singles_bull_throw(
            player1_id=1, player2_id=2, winner_id=2
        )
        assert result.play_order == [2, 1]

    def test_singles_invalid_winner_raises(self) -> None:
        with pytest.raises(ValueError, match="not one of the match players"):
            record_singles_bull_throw(player1_id=1, player2_id=2, winner_id=99)

    # --- Doubles ---

    def test_doubles_team1_player_best(self) -> None:
        """Team1=(1,2), Team2=(3,4). Best=1, best opponent=3."""
        result = record_doubles_bull_throw(
            team1=(1, 2), team2=(3, 4),
            best_player_id=1, best_opponent_id=3,
        )
        assert result.play_order == [1, 3, 2, 4]

    def test_doubles_team2_player_best(self) -> None:
        """Team1=(1,2), Team2=(3,4). Best=4, best opponent=2."""
        result = record_doubles_bull_throw(
            team1=(1, 2), team2=(3, 4),
            best_player_id=4, best_opponent_id=2,
        )
        assert result.play_order == [4, 2, 3, 1]

    def test_doubles_partner_and_remaining_correct(self) -> None:
        """Verify partner of best and remaining opponent are in correct slots."""
        result = record_doubles_bull_throw(
            team1=(10, 20), team2=(30, 40),
            best_player_id=20, best_opponent_id=40,
        )
        # best=20 (team1), partner=10; best_opp=40, remaining=30
        assert result.play_order == [20, 40, 10, 30]

    def test_doubles_best_opponent_wrong_team_raises(self) -> None:
        with pytest.raises(ValueError, match="opposing team"):
            record_doubles_bull_throw(
                team1=(1, 2), team2=(3, 4),
                best_player_id=1, best_opponent_id=2,  # 2 is partner, not opponent
            )

    def test_doubles_best_player_not_in_match_raises(self) -> None:
        with pytest.raises(ValueError, match="not in match"):
            record_doubles_bull_throw(
                team1=(1, 2), team2=(3, 4),
                best_player_id=99, best_opponent_id=3,
            )


# ---------------------------------------------------------------------------
# Dart validation tests
# ---------------------------------------------------------------------------


class TestDartValidation:
    def test_valid_single(self) -> None:
        validate_dart(_single(20))  # should not raise

    def test_valid_double(self) -> None:
        validate_dart(_double(20))

    def test_valid_triple(self) -> None:
        validate_dart(_triple(20))

    def test_valid_bull(self) -> None:
        validate_dart(_bull())

    def test_valid_bullseye(self) -> None:
        validate_dart(_bullseye())

    def test_invalid_single_too_high(self) -> None:
        with pytest.raises(ValueError):
            validate_dart(Dart(score=21, band=DartBand.SINGLE, number=21))

    def test_invalid_double_score(self) -> None:
        with pytest.raises(ValueError):
            validate_dart(Dart(score=41, band=DartBand.DOUBLE, number=21))

    def test_bounce_always_valid(self) -> None:
        d = Dart(score=99, band=DartBand.SINGLE, number=20, bounce=True)
        validate_dart(d)  # should not raise
        assert d.score == 0  # forced to 0 in __post_init__


# ---------------------------------------------------------------------------
# Bust detection tests
# ---------------------------------------------------------------------------


class TestBustDetection:
    def test_overshoot_is_bust(self) -> None:
        """Player on 32 throws 33 → bust, score unchanged."""
        result = _visit(_single(20), _single(10), _single(3), remaining=32)
        assert result.is_bust is True
        assert result.remaining_after == 32
        assert result.total == 0

    def test_reduce_to_one_is_bust_double_out(self) -> None:
        """Player on 3 throws single 2 → remaining 1 → bust (Double-Out)."""
        result = _visit(_single(2), _miss(), _miss(), remaining=3)
        assert result.is_bust is True
        assert result.remaining_after == 3

    def test_reduce_to_one_not_bust_single_out(self) -> None:
        """In Single-Out mode, remaining=1 is NOT automatically a bust
        (player just can't finish on 1, but hasn't busted yet)."""
        # Player on 3, throws S2 → remaining 1 → NOT a bust in Single-Out
        result = _visit(_single(2), _miss(), _miss(), remaining=3, single_out=True)
        assert result.is_bust is False
        assert result.remaining_after == 1

    def test_double_out_valid_finish(self) -> None:
        """Player on 32 throws D16 → valid finish."""
        result = _visit(_double(16), _miss(), _miss(), remaining=32)
        assert result.is_bust is False
        assert result.remaining_after == 0
        assert result.finishing_dart is not None
        assert result.finishing_dart.is_double

    def test_double_out_single_not_valid(self) -> None:
        """Player on 32 throws S16 + S16 → remaining 0 but finishing dart S16 → bust."""
        result = _visit(_single(16), _single(16), _miss(), remaining=32)
        assert result.is_bust is True
        assert result.remaining_after == 32

    def test_bullseye_is_valid_double_out(self) -> None:
        """Player on 50 throws Bullseye → valid Double-Out finish."""
        result = _visit(_bullseye(), _miss(), _miss(), remaining=50)
        assert result.is_bust is False
        assert result.remaining_after == 0
        assert result.finishing_dart is not None
        assert result.finishing_dart.is_bullseye

    def test_normal_visit_no_bust(self) -> None:
        """Player on 501 throws T20, T20, T20 → remaining 321, no bust."""
        result = _visit(_triple(20), _triple(20), _triple(20), remaining=501)
        assert result.is_bust is False
        assert result.remaining_after == 501 - 180
        assert result.total == 180

    def test_single_out_finish_on_single(self) -> None:
        """In Single-Out mode, player on 20 throws S20 → valid finish."""
        result = _visit(_single(20), _miss(), _miss(), remaining=20, single_out=True)
        assert result.is_bust is False
        assert result.remaining_after == 0


# ---------------------------------------------------------------------------
# Single-Out fallback trigger tests
# ---------------------------------------------------------------------------


class TestSingleOutFallback:
    def test_vorrunde_switches_at_16(self) -> None:
        assert should_switch_to_single_out(15, "vorrunde") is False
        assert should_switch_to_single_out(16, "vorrunde") is True

    def test_ko_switches_at_26(self) -> None:
        assert should_switch_to_single_out(25, "ko") is False
        assert should_switch_to_single_out(26, "ko") is True

    def test_lightning_never_switches(self) -> None:
        # Lightning is always Single-Out from the start
        assert should_switch_to_single_out(1, "lightning") is False
        assert should_switch_to_single_out(100, "lightning") is False


# ---------------------------------------------------------------------------
# Checkout suggestion tests — Double-Out (default)
# ---------------------------------------------------------------------------


class TestCheckoutSuggestionsDoubleOut:
    def test_170_checkout(self) -> None:
        """170 = T20, T20, Bullseye (classic Big Fish)."""
        s = get_checkout_suggestion(170)
        assert s is not None
        assert s.is_finish is True
        assert len(s.darts) == 3
        assert s.darts[-1] == "Bullseye"
        assert s.leave == 0

    def test_40_checkout(self) -> None:
        """40 = D20 (one-dart finish)."""
        s = get_checkout_suggestion(40)
        assert s is not None
        assert s.is_finish is True
        assert s.darts == ["D20"]

    def test_2_checkout(self) -> None:
        """2 = D1 (one-dart finish)."""
        s = get_checkout_suggestion(2)
        assert s is not None
        assert s.is_finish is True
        assert s.darts == ["D1"]

    def test_121_checkout(self) -> None:
        """121 is a valid 3-dart Double-Out score."""
        s = get_checkout_suggestion(121)
        assert s is not None
        assert s.is_finish is True
        assert len(s.darts) in (2, 3)
        assert s.darts[-1].startswith("D") or s.darts[-1] == "Bullseye"

    def test_50_checkout_1dart(self) -> None:
        """50 with 1 dart remaining = Bullseye (only option)."""
        s = get_checkout_suggestion(50, darts_remaining=1)
        assert s is not None
        assert s.is_finish is True
        assert s.darts == ["Bullseye"]

    def test_50_checkout_3darts(self) -> None:
        """50 with 3 darts remaining = S18 D16 (user table preference)."""
        s = get_checkout_suggestion(50, darts_remaining=3)
        assert s is not None
        assert s.is_finish is True
        # Table prefers S18+D16 over Bullseye when 3 darts are available
        assert len(s.darts) <= 3
        assert s.leave == 0

    def test_no_checkout_for_1(self) -> None:
        """Score 1 has no valid Double-Out checkout."""
        assert get_checkout_suggestion(1) is None

    def test_no_checkout_above_230(self) -> None:
        """Scores above 230 are outside the display range."""
        assert get_checkout_suggestion(231) is None
        assert get_checkout_suggestion(500) is None

    def test_setup_shot_above_170(self) -> None:
        """Scores 171–230 return setup shots (is_finish=False)."""
        s = get_checkout_suggestion(171)
        assert s is not None
        assert s.is_finish is False
        assert len(s.darts) >= 1

    def test_setup_shot_195_one_dart(self) -> None:
        """195 with 1 dart → setup shot that leaves a checkable score."""
        s = get_checkout_suggestion(195, darts_remaining=1)
        assert s is not None
        assert s.is_finish is False
        assert 2 <= s.leave <= 170

    def test_bogey_has_setup_shot(self) -> None:
        """Bogey numbers can't be finished, but return a setup-shot suggestion."""
        for score in [159, 162, 163, 165, 166, 168, 169]:
            s = get_checkout_suggestion(score)
            assert s is not None, f"Expected setup shot for bogey {score}"
            assert s.is_finish is False, f"Bogey {score} should not be a finish"

    def test_finish_sum_equals_target(self) -> None:
        """For all finishing suggestions 2–170, darts must sum to target."""

        def parse_score(label: str) -> int:
            if label == "Bullseye":
                return 50
            if label == "Bull":
                return 25
            if label.startswith("T"):
                return int(label[1:]) * 3
            if label.startswith("D"):
                return int(label[1:]) * 2
            if label.startswith("S"):
                return int(label[1:])
            return int(label)

        for score in range(2, 171):
            s = get_checkout_suggestion(score)
            if s is not None and s.is_finish:
                total = sum(parse_score(d) for d in s.darts)
                assert total == score, (
                    f"Checkout {s.darts} sums to {total}, not {score}"
                )

    def test_finish_ends_on_double(self) -> None:
        """All finishing suggestions must end on a double."""
        for score in range(2, 171):
            s = get_checkout_suggestion(score)
            if s is not None and s.is_finish:
                last = s.darts[-1]
                assert last.startswith("D") or last == "Bullseye", (
                    f"Score {score}: checkout {s.darts} ends on non-double '{last}'"
                )

    def test_darts_remaining_1_gives_at_most_1_dart(self) -> None:
        """With darts_remaining=1, suggestion has exactly 1 dart."""
        for score in [40, 50, 100, 121, 170]:
            s = get_checkout_suggestion(score, darts_remaining=1)
            if s is not None:
                assert len(s.darts) == 1, (
                    f"Score {score} darts_remaining=1: expected 1 dart, got {s.darts}"
                )

    def test_darts_remaining_2_gives_at_most_2_darts(self) -> None:
        """With darts_remaining=2, suggestion has at most 2 darts."""
        for score in [40, 50, 100, 121, 170]:
            s = get_checkout_suggestion(score, darts_remaining=2)
            if s is not None:
                assert len(s.darts) <= 2, (
                    f"Score {score} darts_remaining=2: too many darts {s.darts}"
                )

    def test_smoke_all_scores_2_to_170(self) -> None:
        """No crash and each result is either None or a valid CheckoutSuggestion."""
        for score in range(2, 171):
            s = get_checkout_suggestion(score)
            assert s is None or isinstance(s, CheckoutSuggestion)
            if s is not None:
                assert isinstance(s.darts, list)
                assert isinstance(s.is_finish, bool)
                assert isinstance(s.leave, int)


# ---------------------------------------------------------------------------
# Checkout suggestion tests — Single-Out
# ---------------------------------------------------------------------------


class TestCheckoutSuggestionsSingleOut:
    def test_single_out_finish_on_single(self) -> None:
        """20 = S20 in Single-Out (no double required)."""
        s = get_checkout_suggestion(20, single_out=True)
        assert s is not None
        assert s.is_finish is True
        assert s.darts == ["S20"]

    def test_single_out_finish_on_bull(self) -> None:
        """25 = Bull in Single-Out."""
        s = get_checkout_suggestion(25, single_out=True)
        assert s is not None
        assert s.is_finish is True
        assert s.darts == ["Bull"]

    def test_single_out_finish_on_bullseye(self) -> None:
        """50 = Bullseye in Single-Out (same as Double-Out)."""
        s = get_checkout_suggestion(50, single_out=True)
        assert s is not None
        assert s.is_finish is True
        assert s.darts == ["Bullseye"]

    def test_single_out_finish_on_triple(self) -> None:
        """60 = T20 in Single-Out (max 1-dart score)."""
        s = get_checkout_suggestion(60, single_out=True)
        assert s is not None
        assert s.is_finish is True
        assert s.darts == ["T20"]

    def test_single_out_3_darts_returns_suggestion(self) -> None:
        """301 starting score; 3-dart suggestion for common remaining values."""
        for score in [80, 100, 121, 160, 180]:
            s = get_checkout_suggestion(score, darts_remaining=3, single_out=True)
            assert s is not None, f"Expected suggestion for single-out {score}"

    def test_single_out_above_180_returns_setup_shot(self) -> None:
        """Scores > 180 in single-out mode return setup shots (e.g. for 301 start)."""
        s = get_checkout_suggestion(181, single_out=True)
        assert s is not None
        assert s.is_finish is False

    def test_single_out_zero_or_negative_returns_none(self) -> None:
        """Score 0 or below has no suggestion."""
        assert get_checkout_suggestion(0, single_out=True) is None
        assert get_checkout_suggestion(-1, single_out=True) is None

    def test_single_out_finish_sum_correct(self) -> None:
        """For all finishing single-out suggestions 1–60, darts must sum to target."""

        def parse_score(label: str) -> int:
            if label == "Bullseye":
                return 50
            if label == "Bull":
                return 25
            if label.startswith("T"):
                return int(label[1:]) * 3
            if label.startswith("D"):
                return int(label[1:]) * 2
            if label.startswith("S"):
                return int(label[1:])
            return int(label)

        for score in range(1, 61):
            s = get_checkout_suggestion(score, single_out=True)
            if s is not None and s.is_finish:
                total = sum(parse_score(d) for d in s.darts)
                assert total == score, (
                    f"Single-Out checkout {s.darts} sums to {total}, not {score}"
                )
