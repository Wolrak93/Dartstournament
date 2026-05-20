"""Tests for the Match Flow Engine (Task 6)."""

from __future__ import annotations

import pytest

from app.services.match import (
    BullThrowRound,
    Dart,
    DartBand,
    VisitResult,
    dart_from_score,
    get_checkout_suggestion,
    process_visit,
    resolve_bull_throw,
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


def _miss() -> Dart:
    return Dart(score=0, band=DartBand.MISS, number=0)


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
    def test_clear_winner(self) -> None:
        rounds = [BullThrowRound(distances={1: 10.0, 2: 20.0, 3: 30.0})]
        result = resolve_bull_throw(rounds)
        assert result.starting_player_id == 1
        assert result.tied_rounds == 0

    def test_tie_resolved_in_second_round(self) -> None:
        rounds = [
            BullThrowRound(distances={1: 10.0, 2: 10.0}),  # tie
            BullThrowRound(distances={1: 15.0, 2: 5.0}),   # player 2 wins
        ]
        result = resolve_bull_throw(rounds)
        assert result.starting_player_id == 2
        assert result.tied_rounds == 1

    def test_still_tied_raises(self) -> None:
        rounds = [
            BullThrowRound(distances={1: 10.0, 2: 10.0}),
            BullThrowRound(distances={1: 8.0, 2: 8.0}),  # still tied
        ]
        with pytest.raises(ValueError, match="still tied"):
            resolve_bull_throw(rounds)

    def test_empty_rounds_raises(self) -> None:
        with pytest.raises(ValueError):
            resolve_bull_throw([])

    def test_three_players_two_tied_one_wins(self) -> None:
        rounds = [
            BullThrowRound(distances={1: 5.0, 2: 5.0, 3: 15.0}),  # p3 out, p1/p2 tied
            BullThrowRound(distances={1: 3.0, 2: 7.0}),              # p1 wins
        ]
        result = resolve_bull_throw(rounds)
        assert result.starting_player_id == 1
        assert result.tied_rounds == 1


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
# Checkout suggestion tests
# ---------------------------------------------------------------------------


class TestCheckoutSuggestions:
    def test_170_checkout(self) -> None:
        """170 = T20, T20, Bullseye (classic Big Fish)."""
        suggestion = get_checkout_suggestion(170)
        assert len(suggestion) == 3
        assert suggestion[-1] == "Bullseye"

    def test_40_checkout(self) -> None:
        """40 = D20 (one-dart finish)."""
        suggestion = get_checkout_suggestion(40)
        assert suggestion == ["D20"]

    def test_2_checkout(self) -> None:
        """2 = D1 (one-dart finish)."""
        suggestion = get_checkout_suggestion(2)
        assert suggestion == ["D1"]

    def test_121_checkout(self) -> None:
        """121 = T20, T11, D? or similar 3-dart path."""
        suggestion = get_checkout_suggestion(121)
        assert len(suggestion) in (2, 3)
        # Final dart must be a double
        last = suggestion[-1]
        assert last.startswith("D") or last == "Bullseye"

    def test_no_checkout_above_170(self) -> None:
        assert get_checkout_suggestion(171) == []
        assert get_checkout_suggestion(500) == []

    def test_no_checkout_for_1(self) -> None:
        assert get_checkout_suggestion(1) == []

    def test_50_checkout(self) -> None:
        """50 = Bullseye (one-dart finish)."""
        suggestion = get_checkout_suggestion(50)
        assert suggestion == ["Bullseye"]

    def test_all_valid_scores_2_to_170_have_suggestion_or_empty(self) -> None:
        """Smoke test: no crash and each result is a list."""
        for score in range(2, 171):
            result = get_checkout_suggestion(score)
            assert isinstance(result, list)
            if result:
                last = result[-1]
                assert last.startswith("D") or last == "Bullseye", (
                    f"Checkout for {score} ends on non-double: {result}"
                )

    def test_checkout_sum_equals_target(self) -> None:
        """Verify that suggested darts actually sum to the target score."""
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
            result = get_checkout_suggestion(score)
            if result:
                total = sum(parse_score(d) for d in result)
                assert total == score, f"Checkout {result} sums to {total}, not {score}"

    def test_unreachable_scores_have_no_suggestion(self) -> None:
        """Certain scores cannot be checked out in 3 darts (bogey numbers)."""
        # These are known impossible checkouts
        impossible = {159, 162, 163, 165, 166, 168, 169}
        for score in impossible:
            result = get_checkout_suggestion(score)
            assert result == [], f"Expected no checkout for {score}, got {result}"
