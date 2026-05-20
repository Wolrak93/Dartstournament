"""Special events detection for the Backsberger Open.

Detects all 19 special events per visit and computes bonus values.
Bonus values are only meaningful in the Vorrunde; in KO and Lightning
rounds the returned bonus_value will always be 0.

Events that can trigger multiple times per visit (Tripel, Bull, etc.)
report their count so the caller can store/display each occurrence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.services.match import Dart, DartBand, VisitResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BOGEY_NUMBERS: frozenset[int] = frozenset([159, 162, 163, 165, 166, 168, 169])

# ---------------------------------------------------------------------------
# Event type catalogue
# ---------------------------------------------------------------------------


class EventType(StrEnum):
    GEWORFEN_26 = "26_geworfen"
    GEWORFEN_180 = "180_geworfen"
    REST_170 = "170_rest"
    KACK_REST = "kack_rest"
    BOGEY = "bogey"
    TRIPEL = "tripel"
    TRIPEL_20 = "tripel_20"
    BULL = "bull"
    BULLSEYE = "bullseye"
    BOUNCE = "bounce"
    ROBIN_HOOD = "robin_hood"
    BE_FINISH = "be_finish"
    ODD_FINISH = "odd_finish"
    DOUBLE_DOUBLE = "double_double"
    MAD_HOUSE = "mad_house"
    SHANGHAI = "shanghai"
    BUST = "bust"
    DOPPEL_TREFFER = "doppel_treffer"
    GLEICHE_ZAHL = "gleiche_zahl"


# Bonus value per single occurrence (Vorrunde only).
_EVENT_VALUE: dict[EventType, int] = {
    EventType.GEWORFEN_26: 26,
    EventType.GEWORFEN_180: 1800,
    EventType.REST_170: 170,
    EventType.KACK_REST: 32,
    EventType.BOGEY: -25,
    EventType.TRIPEL: 3,
    EventType.TRIPEL_20: 17,
    EventType.BULL: 25,
    EventType.BULLSEYE: 50,
    EventType.BOUNCE: -10,
    EventType.ROBIN_HOOD: 65,
    EventType.BE_FINISH: 50,
    EventType.ODD_FINISH: 34,
    EventType.DOUBLE_DOUBLE: 80,
    EventType.MAD_HOUSE: 17,
    EventType.SHANGHAI: 120,
    EventType.BUST: -1,
    EventType.DOPPEL_TREFFER: 8,
    EventType.GLEICHE_ZAHL: 12,
}


@dataclass(frozen=True)
class DetectedEvent:
    """One triggered event from a single visit.

    count       - number of times this event was triggered in the visit.
    bonus_value - total bonus (count × per-event value); always 0 outside
                  Vorrunde.
    """

    event_type: EventType
    count: int
    bonus_value: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _active_darts(darts: list[Dart]) -> list[Dart]:
    """Return darts that physically stuck in the board (no bounce, no RH)."""
    return [d for d in darts if not d.bounce and not d.robin_hood]


def _is_double_field(dart: Dart) -> bool:
    """True for any double ring hit, including bullseye (D25)."""
    return dart.band in (DartBand.DOUBLE, DartBand.BULLSEYE)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_events(
    visit_result: VisitResult,
    remaining_before: int,
    is_vorrunde: bool = True,
) -> list[DetectedEvent]:
    """Detect all triggered special events for a completed visit.

    Args:
        visit_result:     Completed visit returned by process_visit().
        remaining_before: Score before this visit was thrown.
        is_vorrunde:      If False, bonus_value is always 0 (KO/Lightning).

    Returns:
        List of DetectedEvent instances, one per triggered event type.
        The list is in detection order (not sorted by value).
    """
    darts = visit_result.darts
    is_bust = visit_result.is_bust
    remaining_after = visit_result.remaining_after
    finishing = visit_result.finishing_dart

    # VisitResult.total is 0 on a bust; compute actual thrown total from darts.
    thrown_total = sum(d.score for d in darts)

    # Darts that actually registered on the board.
    active = _active_darts(darts)

    triggered: list[DetectedEvent] = []

    def _add(event_type: EventType, count: int = 1) -> None:
        value = _EVENT_VALUE[event_type] * count if is_vorrunde else 0
        triggered.append(
            DetectedEvent(event_type=event_type, count=count, bonus_value=value)
        )

    # ------------------------------------------------------------------
    # Score-total events (only on valid, non-bust visits)
    # ------------------------------------------------------------------

    if not is_bust and thrown_total == 26:
        _add(EventType.GEWORFEN_26)

    if not is_bust and thrown_total == 180:
        _add(EventType.GEWORFEN_180)

    # ------------------------------------------------------------------
    # Remaining-score events (only meaningful on non-bust visits)
    # ------------------------------------------------------------------

    if not is_bust:
        if remaining_after == 170:
            _add(EventType.REST_170)

        if remaining_after in {2, 3}:
            _add(EventType.KACK_REST)

        # Bogey: only when the visit actually changed the score.
        if remaining_after != remaining_before and remaining_after in BOGEY_NUMBERS:
            _add(EventType.BOGEY)

    # ------------------------------------------------------------------
    # Per-dart hit events (counted for each occurrence; bounce/RH excluded)
    # ------------------------------------------------------------------

    tripel_count = sum(1 for d in active if d.band == DartBand.TRIPLE)
    if tripel_count:
        _add(EventType.TRIPEL, tripel_count)

    # Tripel 20 is a narrower subset of Tripel — both can fire for the same dart.
    t20_count = sum(
        1 for d in active if d.band == DartBand.TRIPLE and d.number == 20
    )
    if t20_count:
        _add(EventType.TRIPEL_20, t20_count)

    bull_count = sum(1 for d in active if d.band == DartBand.BULL)
    if bull_count:
        _add(EventType.BULL, bull_count)

    bullseye_count = sum(1 for d in active if d.band == DartBand.BULLSEYE)
    if bullseye_count:
        _add(EventType.BULLSEYE, bullseye_count)

    # Bounce and Robin Hood include the actual flagged darts (all of darts list).
    bounce_count = sum(1 for d in darts if d.bounce)
    if bounce_count:
        _add(EventType.BOUNCE, bounce_count)

    rh_count = sum(1 for d in darts if d.robin_hood)
    if rh_count:
        _add(EventType.ROBIN_HOOD, rh_count)

    # ------------------------------------------------------------------
    # Finish events (game-ending visits only)
    # ------------------------------------------------------------------

    if not is_bust and remaining_after == 0 and finishing is not None:
        if finishing.band == DartBand.BULLSEYE:
            _add(EventType.BE_FINISH)

        # Odd finish: finishing double on an odd number (D1, D3, …, D19).
        # Bullseye (D25) is handled by BE_FINISH; its band is BULLSEYE, not
        # DOUBLE, so it cannot accidentally trigger ODD_FINISH.
        if finishing.band == DartBand.DOUBLE and finishing.number % 2 == 1:
            _add(EventType.ODD_FINISH)

        # Mad House: finish specifically on D1.
        if finishing.band == DartBand.DOUBLE and finishing.number == 1:
            _add(EventType.MAD_HOUSE)

    # ------------------------------------------------------------------
    # Multi-double events (non-bust visits only)
    # ------------------------------------------------------------------

    if not is_bust:
        double_count = sum(1 for d in active if _is_double_field(d))

        if double_count >= 2:
            _add(EventType.DOUBLE_DOUBLE)

        if double_count > 0:
            _add(EventType.DOPPEL_TREFFER, double_count)

    # ------------------------------------------------------------------
    # Shanghai: exactly S + D + T of the same numbered field (1–20)
    # ------------------------------------------------------------------

    numbered = [d for d in active if 1 <= d.number <= 20]
    if len(numbered) == 3:
        unique_numbers = {d.number for d in numbered}
        if len(unique_numbers) == 1:
            bands = {d.band for d in numbered}
            if (
                DartBand.SINGLE in bands
                and DartBand.DOUBLE in bands
                and DartBand.TRIPLE in bands
            ):
                _add(EventType.SHANGHAI)

    # ------------------------------------------------------------------
    # Gleiche Zahl: all 3 (non-miss) active darts on the same number.
    # Shanghai is a special case and both events fire simultaneously.
    # ------------------------------------------------------------------

    non_miss = [d for d in active if d.number != 0]
    if len(non_miss) == 3:
        nums = [d.number for d in non_miss]
        if nums[0] == nums[1] == nums[2]:
            _add(EventType.GLEICHE_ZAHL)

    # ------------------------------------------------------------------
    # Bust
    # ------------------------------------------------------------------

    if is_bust:
        _add(EventType.BUST)

    return triggered


def event_value(event_type: EventType) -> int:
    """Return the per-occurrence bonus value for an event type."""
    return _EVENT_VALUE[event_type]
