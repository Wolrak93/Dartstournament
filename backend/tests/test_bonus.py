"""Tests for the Bonus Points Aggregation service (Task 9)."""

from __future__ import annotations

from app.services.bonus import (
    aggregate_bonus,
    apply_visit_bonus,
    sum_visit_bonus,
    update_standing_bonus,
)
from app.services.events import DetectedEvent, EventType, detect_events
from app.services.match import Dart, DartBand, process_visit
from app.services.vorrunde import PlayerStanding

# ---------------------------------------------------------------------------
# Dart helpers (mirrors test_events.py style)
# ---------------------------------------------------------------------------


def _single(n: int) -> Dart:
    return Dart(score=n, band=DartBand.SINGLE, number=n)


def _triple(n: int) -> Dart:
    return Dart(score=n * 3, band=DartBand.TRIPLE, number=n)


def _miss() -> Dart:
    return Dart(score=0, band=DartBand.MISS, number=0)


def _bullseye() -> Dart:
    return Dart(score=50, band=DartBand.BULLSEYE, number=25)


def _pv(darts: list[Dart], remaining: int) -> object:
    """Run process_visit with sensible defaults."""
    return process_visit(darts, remaining, visit_number=1, single_out_mode=False)


# ---------------------------------------------------------------------------
# sum_visit_bonus
# ---------------------------------------------------------------------------


def test_sum_visit_bonus_empty():
    assert sum_visit_bonus([]) == 0


def test_sum_visit_bonus_single_event():
    events = [DetectedEvent(event_type=EventType.GEWORFEN_26, count=1, bonus_value=26)]
    assert sum_visit_bonus(events) == 26


def test_sum_visit_bonus_multiple_events():
    # Tripel (3) + Tripel 20 (17) triggered by one T20 dart in Vorrunde
    visit = _pv([_triple(20), _single(1), _single(1)], remaining=200)
    events = detect_events(visit, remaining_before=200, is_vorrunde=True)
    total = sum_visit_bonus(events)
    # At minimum Tripel (+3) and Tripel20 (+17) must be present
    assert total >= 20


def test_sum_visit_bonus_negative_event():
    events = [DetectedEvent(event_type=EventType.BUST, count=1, bonus_value=-1)]
    assert sum_visit_bonus(events) == -1


# ---------------------------------------------------------------------------
# apply_visit_bonus — real-time incremental updates
# ---------------------------------------------------------------------------


def test_apply_visit_bonus_initialises_missing_player():
    totals: dict[int, int] = {}
    result = apply_visit_bonus(totals, player_id=1, events=[])
    assert result == 0
    assert totals[1] == 0


def test_apply_visit_bonus_accumulates_over_visits():
    totals: dict[int, int] = {}

    # Visit 1: score 26 → +26
    events1 = [DetectedEvent(event_type=EventType.GEWORFEN_26, count=1, bonus_value=26)]
    apply_visit_bonus(totals, player_id=1, events=events1)
    assert totals[1] == 26

    # Visit 2: bust → -1
    events2 = [DetectedEvent(event_type=EventType.BUST, count=1, bonus_value=-1)]
    apply_visit_bonus(totals, player_id=1, events=events2)
    assert totals[1] == 25

    # Visit 3: T20 → Tripel (+3) + Tripel20 (+17)
    events3 = [
        DetectedEvent(event_type=EventType.TRIPEL, count=1, bonus_value=3),
        DetectedEvent(event_type=EventType.TRIPEL_20, count=1, bonus_value=17),
    ]
    apply_visit_bonus(totals, player_id=1, events=events3)
    assert totals[1] == 45


def test_apply_visit_bonus_tracks_multiple_players_independently():
    totals: dict[int, int] = {}

    ev_p1 = [DetectedEvent(event_type=EventType.GEWORFEN_26, count=1, bonus_value=26)]
    ev_p2 = [
        DetectedEvent(event_type=EventType.GEWORFEN_180, count=1, bonus_value=1800)
    ]

    apply_visit_bonus(totals, player_id=1, events=ev_p1)
    apply_visit_bonus(totals, player_id=2, events=ev_p2)

    assert totals[1] == 26
    assert totals[2] == 1800


# ---------------------------------------------------------------------------
# aggregate_bonus — batch computation
# ---------------------------------------------------------------------------


def test_aggregate_bonus_empty():
    assert aggregate_bonus([]) == {}


def test_aggregate_bonus_single_player_multiple_visits():
    history = [
        (1, [DetectedEvent(event_type=EventType.GEWORFEN_26, count=1, bonus_value=26)]),
        (1, [DetectedEvent(event_type=EventType.TRIPEL, count=2, bonus_value=6)]),
        (1, [DetectedEvent(event_type=EventType.BUST, count=1, bonus_value=-1)]),
    ]
    result = aggregate_bonus(history)
    assert result == {1: 31}


def test_aggregate_bonus_multiple_players():
    ev_180 = DetectedEvent(event_type=EventType.GEWORFEN_180, count=1, bonus_value=1800)
    history = [
        (1, [ev_180]),
        (2, [DetectedEvent(event_type=EventType.GEWORFEN_26, count=1, bonus_value=26)]),
        (1, [DetectedEvent(event_type=EventType.BULL, count=1, bonus_value=25)]),
        (2, [DetectedEvent(event_type=EventType.BUST, count=1, bonus_value=-1)]),
    ]
    result = aggregate_bonus(history)
    assert result == {1: 1825, 2: 25}


def test_aggregate_bonus_returns_zero_for_no_events():
    history = [(1, []), (2, [])]
    result = aggregate_bonus(history)
    assert result == {1: 0, 2: 0}


# ---------------------------------------------------------------------------
# KO events produce 0 bonus — must not add to total
# ---------------------------------------------------------------------------


def test_ko_events_have_zero_bonus_value():
    """detect_events with is_vorrunde=False must return bonus_value=0 for all events."""
    # T20 in a KO match: would give +3 and +17 in Vorrunde, but 0 here.
    visit = _pv([_triple(20), _single(1), _single(1)], remaining=200)
    events = detect_events(visit, remaining_before=200, is_vorrunde=False)
    for ev in events:
        assert ev.bonus_value == 0, (
            f"KO event {ev.event_type} should have bonus_value=0, got {ev.bonus_value}"
        )


def test_ko_events_do_not_increase_running_total():
    """Applying KO visit events must leave the running total unchanged."""
    totals: dict[int, int] = {1: 100}

    # Simulate a KO visit with a spectacular T20 — should add 0
    visit = _pv([_triple(20), _triple(20), _triple(20)], remaining=200)
    ko_events = detect_events(visit, remaining_before=200, is_vorrunde=False)

    apply_visit_bonus(totals, player_id=1, events=ko_events)
    assert totals[1] == 100


def test_aggregate_bonus_ignores_ko_events():
    """aggregate_bonus on a mix of Vorrunde and KO visits counts only Vorrunde."""
    vorrunde_visit = _pv([_single(1), _single(5), _single(20)], remaining=300)
    vorrunde_events = detect_events(
        vorrunde_visit, remaining_before=300, is_vorrunde=True
    )

    ko_visit = _pv([_triple(20), _triple(20), _triple(20)], remaining=200)
    ko_events = detect_events(ko_visit, remaining_before=200, is_vorrunde=False)

    history = [
        (1, vorrunde_events),  # +26 from score_26
        (1, ko_events),        # all zeros
    ]
    result = aggregate_bonus(history)
    assert result[1] == sum_visit_bonus(vorrunde_events)


# ---------------------------------------------------------------------------
# update_standing_bonus — PlayerStanding integration
# ---------------------------------------------------------------------------


def test_update_standing_bonus_increments_bonus_points():
    standing = PlayerStanding(player_id=42)
    assert standing.bonus_points == 0

    events = [DetectedEvent(event_type=EventType.GEWORFEN_26, count=1, bonus_value=26)]
    update_standing_bonus(standing, events)
    assert standing.bonus_points == 26


def test_update_standing_bonus_accumulates_across_calls():
    standing = PlayerStanding(player_id=7)

    update_standing_bonus(
        standing,
        [DetectedEvent(event_type=EventType.TRIPEL, count=3, bonus_value=9)],
    )
    update_standing_bonus(
        standing,
        [DetectedEvent(event_type=EventType.BULL, count=1, bonus_value=25)],
    )
    assert standing.bonus_points == 34


def test_update_standing_bonus_ko_events_leave_standing_unchanged():
    standing = PlayerStanding(player_id=3)
    standing.bonus_points = 50  # some prior Vorrunde bonus

    # Bullseye finish: dart1 hits bullseye (50), remaining darts are misses
    visit = _pv([_bullseye(), _miss(), _miss()], remaining=50)
    ko_events = detect_events(visit, remaining_before=50, is_vorrunde=False)
    update_standing_bonus(standing, ko_events)

    # KO finish: all bonus_values are 0, so standing must stay at 50
    assert standing.bonus_points == 50
