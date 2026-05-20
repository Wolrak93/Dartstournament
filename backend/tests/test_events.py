"""Tests for the Special Events Detection Engine (Task 8)."""

from __future__ import annotations

import pytest
from conftest import _miss  # shared helper; defined once in conftest.py

from app.services.events import (
    DetectedEvent,
    EventType,
    detect_events,
    event_value,
)
from app.services.match import (
    Dart,
    DartBand,
    VisitResult,
    process_visit,
)

# ---------------------------------------------------------------------------
# Test helpers — shorthand dart constructors
# ---------------------------------------------------------------------------


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


def _bounce(n: int) -> Dart:
    """A dart that bounced out of the triple-n field."""
    return Dart(score=n * 3, band=DartBand.TRIPLE, number=n, bounce=True)


def _robin_hood(n: int) -> Dart:
    """A dart that got a Robin Hood in the single-n field."""
    return Dart(score=n, band=DartBand.SINGLE, number=n, robin_hood=True)


def _pv(darts: list[Dart], remaining: int, single_out: bool = False) -> VisitResult:
    """Shorthand for process_visit."""
    return process_visit(darts, remaining, visit_number=1, single_out_mode=single_out)


def _make_visit(
    darts: list[Dart],
    remaining: int,
    single_out: bool = False,
) -> VisitResult:
    """Build a VisitResult via the real process_visit function."""
    return _pv(darts, remaining, single_out)


def _event_types(events: list[DetectedEvent]) -> set[EventType]:
    return {e.event_type for e in events}


def _get(events: list[DetectedEvent], et: EventType) -> DetectedEvent | None:
    for e in events:
        if e.event_type == et:
            return e
    return None


# ---------------------------------------------------------------------------
# 1. 26 geworfen
# ---------------------------------------------------------------------------


def test_26_geworfen_triggers():
    # Classic S1 + S5 + S20
    visit = _make_visit([_single(1), _single(5), _single(20)], remaining=200)
    events = detect_events(visit, remaining_before=200)
    assert EventType.GEWORFEN_26 in _event_types(events)
    ev = _get(events, EventType.GEWORFEN_26)
    assert ev is not None
    assert ev.bonus_value == 26


def test_26_geworfen_no_trigger_on_other_totals():
    visit = _make_visit([_single(1), _single(1), _single(1)], remaining=200)
    events = detect_events(visit, remaining_before=200)
    assert EventType.GEWORFEN_26 not in _event_types(events)


def test_26_geworfen_no_trigger_on_bust():
    # Remaining=20, throw 26 → bust → no event
    visit = _make_visit([_single(1), _single(5), _single(20)], remaining=20)
    assert visit.is_bust
    events = detect_events(visit, remaining_before=20)
    assert EventType.GEWORFEN_26 not in _event_types(events)


# ---------------------------------------------------------------------------
# 2. 180 geworfen
# ---------------------------------------------------------------------------


def test_180_geworfen_triggers():
    visit = _make_visit([_triple(20), _triple(20), _triple(20)], remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.GEWORFEN_180 in _event_types(events)
    ev = _get(events, EventType.GEWORFEN_180)
    assert ev is not None
    assert ev.bonus_value == 1800


def test_180_geworfen_no_trigger_on_bust():
    # Remaining=120, throw 180 → bust
    visit = _make_visit([_triple(20), _triple(20), _triple(20)], remaining=120)
    assert visit.is_bust
    events = detect_events(visit, remaining_before=120)
    assert EventType.GEWORFEN_180 not in _event_types(events)


# ---------------------------------------------------------------------------
# 3. 170 Rest
# ---------------------------------------------------------------------------


def test_170_rest_triggers():
    # Remaining 230, throw T20=60 → remaining 170
    visit = _make_visit([_triple(20), _miss(), _miss()], remaining=230)
    assert visit.remaining_after == 170
    events = detect_events(visit, remaining_before=300)
    assert EventType.REST_170 in _event_types(events)
    ev = _get(events, EventType.REST_170)
    assert ev is not None
    assert ev.bonus_value == 170


def test_170_rest_no_trigger_on_bust():
    # Can't leave 170 on a bust (remaining stays same)
    visit = _make_visit([_triple(20), _triple(20), _triple(20)], remaining=120)
    assert visit.is_bust
    events = detect_events(visit, remaining_before=120)
    assert EventType.REST_170 not in _event_types(events)


# ---------------------------------------------------------------------------
# 4. Kack-Rest
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rest,score", [(2, 18), (3, 17)])
def test_kack_rest_triggers(rest: int, score: int):
    # Remaining=20, throw single score → leave rest (2 or 3)
    visit = _make_visit([_single(score), _miss(), _miss()], remaining=20)
    assert visit.remaining_after == rest
    events = detect_events(visit, remaining_before=20)
    assert EventType.KACK_REST in _event_types(events)


def test_kack_rest_no_trigger_on_bust():
    # Throw enough to bust while remaining is 3 → remaining stays 3, but is_bust=True
    # In Double-Out mode, remaining=3 and score=4 → bust
    visit = _make_visit([_single(4), _miss(), _miss()], remaining=3)
    assert visit.is_bust
    events = detect_events(visit, remaining_before=3)
    assert EventType.KACK_REST not in _event_types(events)


# ---------------------------------------------------------------------------
# 5. Bogey
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bogey", [159, 162, 163, 165, 166, 168, 169])
def test_bogey_triggers(bogey: int):
    # Start at bogey+60 (throw T20=60 to land on bogey), safe remaining
    start = bogey + 60
    visit = _make_visit([_triple(20), _miss(), _miss()], remaining=start)
    assert visit.remaining_after == bogey
    events = detect_events(visit, remaining_before=start)
    assert EventType.BOGEY in _event_types(events)
    ev = _get(events, EventType.BOGEY)
    assert ev is not None
    assert ev.bonus_value == -25


def test_bogey_no_trigger_on_non_bogey():
    visit = _make_visit([_triple(20), _miss(), _miss()], remaining=300)
    assert visit.remaining_after == 240
    events = detect_events(visit, remaining_before=300)
    assert EventType.BOGEY not in _event_types(events)


def test_bogey_no_trigger_when_already_at_bogey_and_bust():
    # Remaining already is 162 (bogey); busting keeps it at 162, but no new bogey.
    # T20+T20+T20=180 > 162 → bust; remaining stays 162.
    visit = _make_visit([_triple(20), _triple(20), _triple(20)], remaining=162)
    assert visit.is_bust
    events = detect_events(visit, remaining_before=162)
    assert EventType.BOGEY not in _event_types(events)


# ---------------------------------------------------------------------------
# 6. Tripel
# ---------------------------------------------------------------------------


def test_tripel_single_occurrence():
    visit = _make_visit([_triple(5), _single(1), _single(1)], remaining=300)
    events = detect_events(visit, remaining_before=300)
    ev = _get(events, EventType.TRIPEL)
    assert ev is not None
    assert ev.count == 1
    assert ev.bonus_value == 3


def test_tripel_multiple_occurrences():
    visit = _make_visit([_triple(5), _triple(10), _triple(1)], remaining=300)
    events = detect_events(visit, remaining_before=300)
    ev = _get(events, EventType.TRIPEL)
    assert ev is not None
    assert ev.count == 3
    assert ev.bonus_value == 9  # 3 × 3


def test_tripel_no_trigger_on_miss():
    visit = _make_visit([_miss(), _miss(), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.TRIPEL not in _event_types(events)


def test_tripel_bounce_not_counted():
    # Bounce dart has bounce=True; should not count as Tripel hit.
    bounce = _bounce(20)
    visit = _pv([bounce, _miss(), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.TRIPEL not in _event_types(events)
    # But BOUNCE event should fire
    assert EventType.BOUNCE in _event_types(events)


# ---------------------------------------------------------------------------
# 7. Tripel 20
# ---------------------------------------------------------------------------


def test_tripel_20_triggers_and_also_fires_tripel():
    visit = _make_visit([_triple(20), _single(1), _single(1)], remaining=300)
    events = detect_events(visit, remaining_before=300)
    ev20 = _get(events, EventType.TRIPEL_20)
    assert ev20 is not None
    assert ev20.count == 1
    assert ev20.bonus_value == 17
    # Tripel also fires
    assert EventType.TRIPEL in _event_types(events)


def test_tripel_20_count_two():
    visit = _make_visit([_triple(20), _triple(20), _single(1)], remaining=300)
    events = detect_events(visit, remaining_before=300)
    ev = _get(events, EventType.TRIPEL_20)
    assert ev is not None
    assert ev.count == 2
    assert ev.bonus_value == 34


def test_tripel_not_20_does_not_trigger_tripel_20():
    visit = _make_visit([_triple(19), _miss(), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.TRIPEL_20 not in _event_types(events)
    assert EventType.TRIPEL in _event_types(events)


# ---------------------------------------------------------------------------
# 8. Bull (single bull)
# ---------------------------------------------------------------------------


def test_bull_triggers():
    visit = _make_visit([_bull(), _miss(), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    ev = _get(events, EventType.BULL)
    assert ev is not None
    assert ev.count == 1
    assert ev.bonus_value == 25


def test_bull_multiple():
    visit = _make_visit([_bull(), _bull(), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    ev = _get(events, EventType.BULL)
    assert ev is not None
    assert ev.count == 2
    assert ev.bonus_value == 50


# ---------------------------------------------------------------------------
# 9. Bulls Eye (double bull)
# ---------------------------------------------------------------------------


def test_bullseye_triggers():
    visit = _make_visit([_bullseye(), _miss(), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    ev = _get(events, EventType.BULLSEYE)
    assert ev is not None
    assert ev.count == 1
    assert ev.bonus_value == 50


# ---------------------------------------------------------------------------
# 10. Bounce
# ---------------------------------------------------------------------------


def test_bounce_triggers():
    bounce = _bounce(20)
    visit = _pv([bounce, _miss(), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    ev = _get(events, EventType.BOUNCE)
    assert ev is not None
    assert ev.count == 1
    assert ev.bonus_value == -10


def test_bounce_multiple():
    b1, b2 = _bounce(20), _bounce(5)
    visit = _pv([b1, b2, _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    ev = _get(events, EventType.BOUNCE)
    assert ev is not None
    assert ev.count == 2
    assert ev.bonus_value == -20


# ---------------------------------------------------------------------------
# 11. Robin Hood
# ---------------------------------------------------------------------------


def test_robin_hood_triggers():
    rh = _robin_hood(20)
    visit = _pv([rh, _miss(), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    ev = _get(events, EventType.ROBIN_HOOD)
    assert ev is not None
    assert ev.count == 1
    assert ev.bonus_value == 65


def test_robin_hood_not_counted_as_tripel():
    # Robin Hood dart's band is SINGLE in our helper; shouldn't fire Tripel.
    rh = _robin_hood(5)
    visit = _pv([rh, _miss(), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.TRIPEL not in _event_types(events)
    assert EventType.ROBIN_HOOD in _event_types(events)


# ---------------------------------------------------------------------------
# 12. BE Finish
# ---------------------------------------------------------------------------


def test_be_finish_triggers():
    # Finish on bullseye: remaining 50
    visit = _make_visit([_bullseye(), _miss(), _miss()], remaining=50)
    assert visit.remaining_after == 0
    events = detect_events(visit, remaining_before=50)
    assert EventType.BE_FINISH in _event_types(events)
    ev = _get(events, EventType.BE_FINISH)
    assert ev is not None
    assert ev.bonus_value == 50
    # BULLSEYE hit event also fires
    assert EventType.BULLSEYE in _event_types(events)


def test_be_finish_no_trigger_without_finish():
    visit = _make_visit([_bullseye(), _miss(), _miss()], remaining=200)
    events = detect_events(visit, remaining_before=200)
    assert EventType.BE_FINISH not in _event_types(events)


# ---------------------------------------------------------------------------
# 13. odd Finish
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n", [1, 3, 5, 7, 9, 11, 13, 15, 17, 19])
def test_odd_finish_triggers(n: int):
    # Finish on D_n (odd double)
    visit = _make_visit([_double(n), _miss(), _miss()], remaining=n * 2)
    assert visit.remaining_after == 0
    events = detect_events(visit, remaining_before=n * 2)
    assert EventType.ODD_FINISH in _event_types(events)
    ev = _get(events, EventType.ODD_FINISH)
    assert ev is not None
    assert ev.bonus_value == 34


@pytest.mark.parametrize("n", [2, 4, 6, 8, 10, 12, 14, 16, 18, 20])
def test_odd_finish_no_trigger_on_even_double(n: int):
    visit = _make_visit([_double(n), _miss(), _miss()], remaining=n * 2)
    assert visit.remaining_after == 0
    events = detect_events(visit, remaining_before=n * 2)
    assert EventType.ODD_FINISH not in _event_types(events)


def test_bullseye_finish_does_not_trigger_odd_finish():
    # D25 (bullseye) is handled by BE_FINISH, not odd_finish
    visit = _make_visit([_bullseye(), _miss(), _miss()], remaining=50)
    events = detect_events(visit, remaining_before=50)
    assert EventType.ODD_FINISH not in _event_types(events)
    assert EventType.BE_FINISH in _event_types(events)


# ---------------------------------------------------------------------------
# 14. Double Double
# ---------------------------------------------------------------------------


def test_double_double_triggers_with_two_doubles():
    # D20 + D5 in one visit (not a finish from 200 remaining)
    visit = _make_visit([_double(20), _double(5), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.DOUBLE_DOUBLE in _event_types(events)
    ev = _get(events, EventType.DOUBLE_DOUBLE)
    assert ev is not None
    assert ev.bonus_value == 80


def test_double_double_no_trigger_with_one_double():
    visit = _make_visit([_double(20), _single(1), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.DOUBLE_DOUBLE not in _event_types(events)


def test_double_double_no_trigger_on_bust():
    # Two doubles but it's a bust
    visit = _make_visit([_double(20), _double(20), _miss()], remaining=40)
    # 40+40=80 > 40 → bust (remaining=40, new_remaining=-40 < 0)
    # Wait: remaining=40, total=80, 40-80=-40 < 0 → bust
    # But D20+D20 would be 40+40=80 which > 40 → bust? Yes.
    # Actually D20=40, D20=40, total=80 which > remaining=40 → bust
    assert visit.is_bust
    events = detect_events(visit, remaining_before=40)
    assert EventType.DOUBLE_DOUBLE not in _event_types(events)


# ---------------------------------------------------------------------------
# 15. Mad House
# ---------------------------------------------------------------------------


def test_mad_house_triggers():
    visit = _make_visit([_double(1), _miss(), _miss()], remaining=2)
    assert visit.remaining_after == 0
    events = detect_events(visit, remaining_before=2)
    assert EventType.MAD_HOUSE in _event_types(events)
    ev = _get(events, EventType.MAD_HOUSE)
    assert ev is not None
    assert ev.bonus_value == 17
    # Also triggers odd Finish (D1 is an odd double)
    assert EventType.ODD_FINISH in _event_types(events)


def test_mad_house_no_trigger_on_d2():
    visit = _make_visit([_double(2), _miss(), _miss()], remaining=4)
    assert visit.remaining_after == 0
    events = detect_events(visit, remaining_before=4)
    assert EventType.MAD_HOUSE not in _event_types(events)


# ---------------------------------------------------------------------------
# 16. Shanghai
# ---------------------------------------------------------------------------


def test_shanghai_triggers():
    # S20, D20, T20 in any order
    darts = [_single(20), _double(20), _triple(20)]
    visit = _pv(darts, remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.SHANGHAI in _event_types(events)
    ev = _get(events, EventType.SHANGHAI)
    assert ev is not None
    assert ev.bonus_value == 120
    # Gleiche Zahl also triggers (all same number)
    assert EventType.GLEICHE_ZAHL in _event_types(events)


def test_shanghai_no_trigger_without_all_three_bands():
    # S20, S20, T20 — missing Double
    darts = [_single(20), _single(20), _triple(20)]
    visit = _pv(darts, remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.SHANGHAI not in _event_types(events)
    # But Gleiche Zahl triggers (all number=20)
    assert EventType.GLEICHE_ZAHL in _event_types(events)


def test_shanghai_no_trigger_different_numbers():
    # S20, D19, T18 — all different numbers
    darts = [_single(20), _double(19), _triple(18)]
    visit = _pv(darts, remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.SHANGHAI not in _event_types(events)
    assert EventType.GLEICHE_ZAHL not in _event_types(events)


# ---------------------------------------------------------------------------
# 17. Bust
# ---------------------------------------------------------------------------


def test_bust_triggers():
    # Remaining 20, throw S20+S1+S1=22 → bust
    visit = _make_visit([_single(20), _single(1), _single(1)], remaining=20)
    assert visit.is_bust
    events = detect_events(visit, remaining_before=20)
    assert EventType.BUST in _event_types(events)
    ev = _get(events, EventType.BUST)
    assert ev is not None
    assert ev.bonus_value == -1


def test_bust_no_trigger_on_normal_visit():
    visit = _make_visit([_single(20), _single(1), _single(1)], remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.BUST not in _event_types(events)


# ---------------------------------------------------------------------------
# 18. Doppel-Treffer
# ---------------------------------------------------------------------------


def test_doppel_treffer_triggers_once():
    visit = _make_visit([_double(10), _single(1), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    ev = _get(events, EventType.DOPPEL_TREFFER)
    assert ev is not None
    assert ev.count == 1
    assert ev.bonus_value == 8


def test_doppel_treffer_triggers_twice():
    visit = _make_visit([_double(10), _double(5), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    ev = _get(events, EventType.DOPPEL_TREFFER)
    assert ev is not None
    assert ev.count == 2
    assert ev.bonus_value == 16


def test_doppel_treffer_no_trigger_on_bust():
    # D20 + D20 = 80 > remaining(40) → bust
    visit = _make_visit([_double(20), _double(20), _miss()], remaining=40)
    assert visit.is_bust
    events = detect_events(visit, remaining_before=40)
    assert EventType.DOPPEL_TREFFER not in _event_types(events)


def test_doppel_treffer_bullseye_counts_as_double():
    # Bullseye is D25; should count for Doppel-Treffer
    visit = _make_visit([_bullseye(), _miss(), _miss()], remaining=200)
    events = detect_events(visit, remaining_before=200)
    ev = _get(events, EventType.DOPPEL_TREFFER)
    assert ev is not None
    assert ev.count == 1


# ---------------------------------------------------------------------------
# 19. Gleiche Zahl
# ---------------------------------------------------------------------------


def test_gleiche_zahl_triggers():
    # All three singles on number 7
    visit = _make_visit([_single(7), _single(7), _single(7)], remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.GLEICHE_ZAHL in _event_types(events)
    ev = _get(events, EventType.GLEICHE_ZAHL)
    assert ev is not None
    assert ev.bonus_value == 12


def test_gleiche_zahl_mixed_bands_same_number():
    # S19, D19, S19 — all number=19, different bands (not Shanghai since no Triple)
    darts = [_single(19), _double(19), _single(19)]
    visit = _pv(darts, remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.GLEICHE_ZAHL in _event_types(events)
    assert EventType.SHANGHAI not in _event_types(events)


def test_gleiche_zahl_no_trigger_with_miss():
    # Two of same number + miss → only 2 valid darts, not 3
    visit = _make_visit([_single(7), _single(7), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.GLEICHE_ZAHL not in _event_types(events)


def test_gleiche_zahl_no_trigger_mixed_numbers():
    visit = _make_visit([_single(7), _single(7), _single(8)], remaining=300)
    events = detect_events(visit, remaining_before=300)
    assert EventType.GLEICHE_ZAHL not in _event_types(events)


# ---------------------------------------------------------------------------
# Combined event tests
# ---------------------------------------------------------------------------


def test_mad_house_also_triggers_odd_finish():
    visit = _make_visit([_double(1), _miss(), _miss()], remaining=2)
    events = detect_events(visit, remaining_before=2)
    event_set = _event_types(events)
    assert EventType.MAD_HOUSE in event_set
    assert EventType.ODD_FINISH in event_set


def test_t20_triggers_both_tripel_and_tripel_20():
    visit = _make_visit([_triple(20), _miss(), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    event_set = _event_types(events)
    assert EventType.TRIPEL in event_set
    assert EventType.TRIPEL_20 in event_set


def test_shanghai_triggers_gleiche_zahl():
    darts = [_single(15), _double(15), _triple(15)]
    visit = _pv(darts, remaining=300)
    events = detect_events(visit, remaining_before=300)
    event_set = _event_types(events)
    assert EventType.SHANGHAI in event_set
    assert EventType.GLEICHE_ZAHL in event_set


def test_double_double_and_doppel_treffer_both_fire():
    visit = _make_visit([_double(10), _double(5), _miss()], remaining=300)
    events = detect_events(visit, remaining_before=300)
    event_set = _event_types(events)
    assert EventType.DOUBLE_DOUBLE in event_set
    assert EventType.DOPPEL_TREFFER in event_set


def test_be_finish_also_fires_bullseye_event():
    visit = _make_visit([_bullseye(), _miss(), _miss()], remaining=50)
    events = detect_events(visit, remaining_before=50)
    event_set = _event_types(events)
    assert EventType.BE_FINISH in event_set
    assert EventType.BULLSEYE in event_set


# ---------------------------------------------------------------------------
# KO / Lightning context: events detected but bonus_value = 0
# ---------------------------------------------------------------------------


def test_ko_context_bonus_is_zero():
    visit = _make_visit([_triple(20), _triple(20), _triple(20)], remaining=300)
    events = detect_events(visit, remaining_before=300, is_vorrunde=False)
    assert EventType.GEWORFEN_180 in _event_types(events)
    for ev in events:
        assert ev.bonus_value == 0, f"{ev.event_type} should have bonus_value=0 in KO"


def test_vorrunde_context_bonus_is_nonzero():
    visit = _make_visit([_triple(20), _triple(20), _triple(20)], remaining=300)
    events = detect_events(visit, remaining_before=300, is_vorrunde=True)
    ev_180 = _get(events, EventType.GEWORFEN_180)
    assert ev_180 is not None
    assert ev_180.bonus_value == 1800


def test_ko_context_bust_bonus_zero():
    visit = _make_visit([_single(20), _single(1), _single(1)], remaining=20)
    assert visit.is_bust
    events = detect_events(visit, remaining_before=20, is_vorrunde=False)
    assert EventType.BUST in _event_types(events)
    bust_ev = _get(events, EventType.BUST)
    assert bust_ev is not None
    assert bust_ev.bonus_value == 0


# ---------------------------------------------------------------------------
# event_value() helper
# ---------------------------------------------------------------------------


def test_event_value_returns_correct_values():
    assert event_value(EventType.GEWORFEN_180) == 1800
    assert event_value(EventType.BUST) == -1
    assert event_value(EventType.BOGEY) == -25
    assert event_value(EventType.ROBIN_HOOD) == 65
