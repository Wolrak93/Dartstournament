"""Bonus points aggregation for the Backsberger Open.

Aggregates special event bonus values per player across Vorrunde visits.
KO and Lightning round events always carry bonus_value=0 (enforced by the
events detection engine), so they are naturally excluded from all totals.

The three public functions cover the full lifecycle:

- sum_visit_bonus   — total bonus for a single visit's event list
- apply_visit_bonus — real-time incremental update into a running dict
- aggregate_bonus   — batch computation from an ordered visit history
"""

from __future__ import annotations

from app.services.events import DetectedEvent
from app.services.vorrunde import PlayerStanding

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def sum_visit_bonus(events: list[DetectedEvent]) -> int:
    """Return the total bonus points earned in a single visit.

    Args:
        events: Detected events returned by detect_events() for one visit.

    Returns:
        Sum of bonus_value across all events.  Always 0 for KO/Lightning
        visits because the events engine sets bonus_value=0 in those rounds.
    """
    return sum(e.bonus_value for e in events)


def apply_visit_bonus(
    bonus_totals: dict[int, int],
    player_id: int,
    events: list[DetectedEvent],
) -> int:
    """Incrementally add a visit's bonus to a running per-player total.

    Designed for real-time use: call once after each visit is processed.

    Args:
        bonus_totals: Mutable mapping of player_id → cumulative bonus.
                      Modified in-place.
        player_id:    Player who threw the visit.
        events:       Events detected for that visit.

    Returns:
        Updated cumulative bonus for the player after this visit.
    """
    delta = sum_visit_bonus(events)
    bonus_totals[player_id] = bonus_totals.get(player_id, 0) + delta
    return bonus_totals[player_id]


def aggregate_bonus(
    events_per_visit: list[tuple[int, list[DetectedEvent]]],
) -> dict[int, int]:
    """Compute total bonus points per player from an ordered visit history.

    Useful for recalculating totals from scratch (e.g. after loading from DB).

    Args:
        events_per_visit: List of (player_id, events) pairs in visit order.

    Returns:
        Dict mapping player_id → total bonus points.
    """
    totals: dict[int, int] = {}
    for player_id, events in events_per_visit:
        apply_visit_bonus(totals, player_id, events)
    return totals


def update_standing_bonus(
    standing: PlayerStanding,
    events: list[DetectedEvent],
) -> None:
    """Add a visit's bonus directly to a PlayerStanding object in-place.

    Convenience wrapper for use alongside record_match_result() in vorrunde.py.

    Args:
        standing: The PlayerStanding to update.
        events:   Events detected for the player's visit.
    """
    standing.bonus_points += sum_visit_bonus(events)


# ---------------------------------------------------------------------------
# Persistence helpers (require an async DB session)
# ---------------------------------------------------------------------------


async def load_bonus_from_db(
    db: object,
    tournament_id: int,
    player_id: int,
) -> int:
    """Load a player's total Vorrunde bonus points directly from the DB.

    Reads from the SpecialEvent table instead of in-memory accumulated totals.
    Useful for restoring state after a server restart or for audit purposes.

    Args:
        db:            Async SQLAlchemy session.
        tournament_id: DB id of the tournament.
        player_id:     DB id of the player.

    Returns:
        Total bonus points earned by the player in Vorrunde matches.
    """
    from app.repositories.special_event_repo import sum_bonus_by_player_and_tournament

    return await sum_bonus_by_player_and_tournament(db, tournament_id, player_id)
