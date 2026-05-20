"""Match flow engine for the Backsberger Open.

Handles:
- Bull throw (closest to bull determines who goes first; tie → re-throw)
- Score entry and validation per visit (dart1, dart2, dart3)
- Bust detection (Double-Out and Single-Out rules)
- Single-Out fallback after visit limit (15 Vorrunde / 25 KO)
- Checkout suggestions for remaining scores 2–170
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VORRUNDE_SINGLE_OUT_VISIT: int = 15  # switch to Single-Out after this many visits
KO_SINGLE_OUT_VISIT: int = 25

# Valid single-field values (1–20 + bull values)
SINGLE_FIELDS: frozenset[int] = frozenset(range(1, 21)) | {25, 50}

# Bogey numbers (impossible to finish from in Double-Out)
BOGEY_NUMBERS: frozenset[int] = frozenset([159, 162, 163, 165, 166, 168, 169])

# ---------------------------------------------------------------------------
# Dart representation
# ---------------------------------------------------------------------------


class DartBand(StrEnum):
    """Which ring a dart landed in."""

    MISS = "miss"
    SINGLE = "single"
    DOUBLE = "double"
    TRIPLE = "triple"
    BULL = "bull"        # single bull (25)
    BULLSEYE = "bullseye"  # double bull (50)


@dataclass
class Dart:
    """A single dart throw.

    score  - raw score value (0–60, 25, 50)
    band   - which ring it landed in (used for event detection)
    number - the number field hit (1–20, 25 for bull/bullseye); 0 for miss
    bounce - True if the dart bounced out (referee flag)
    robin_hood - True if dart stuck in another dart (referee flag)
    """

    score: int
    band: DartBand
    number: int = 0
    bounce: bool = False
    robin_hood: bool = False

    def __post_init__(self) -> None:
        if self.bounce or self.robin_hood:
            # These darts score 0 regardless
            self.score = 0

    @property
    def is_double(self) -> bool:
        return self.band in (DartBand.DOUBLE, DartBand.BULLSEYE)

    @property
    def is_triple(self) -> bool:
        return self.band == DartBand.TRIPLE

    @property
    def is_bull(self) -> bool:
        return self.band == DartBand.BULL

    @property
    def is_bullseye(self) -> bool:
        return self.band == DartBand.BULLSEYE


def dart_from_score(score: int) -> Dart:
    """Convenience: infer a Dart from its numeric score only.

    Used when the referee enters a plain number (total visit or single dart score)
    without specifying the band.  This is a best-effort inference:

    - 0        → miss
    - 25       → single bull
    - 50       → bullseye
    - 1–20     → single field (number = score)
    - 21–40    → double field  (number = score // 2)  e.g. 40 → D20
    - 42–60    → triple field  (number = score // 3)  e.g. 60 → T20
    - 22,26,34,38 are ambiguous doubles; 44,46,52,56,58 are ambiguous triples.

    For unambiguous band inference we use the following priority:
      triple > double > single (if multiple bands could produce the score)
    """
    if score == 0:
        return Dart(score=0, band=DartBand.MISS, number=0)
    if score == 25:
        return Dart(score=25, band=DartBand.BULL, number=25)
    if score == 50:
        return Dart(score=50, band=DartBand.BULLSEYE, number=25)
    # Triple check first (scores 3,6,...60 divisible by 3 and number 1-20)
    if score % 3 == 0 and 1 <= score // 3 <= 20:
        return Dart(score=score, band=DartBand.TRIPLE, number=score // 3)
    # Double check (scores 2,4,...40 divisible by 2 and number 1-20)
    if score % 2 == 0 and 1 <= score // 2 <= 20:
        return Dart(score=score, band=DartBand.DOUBLE, number=score // 2)
    # Single field (1-20)
    if 1 <= score <= 20:
        return Dart(score=score, band=DartBand.SINGLE, number=score)
    raise ValueError(f"Cannot infer dart from score {score}")


def validate_dart(dart: Dart) -> None:
    """Raise ValueError if dart has an illegal score/band combination."""
    if dart.bounce or dart.robin_hood:
        return  # always valid; score forced to 0 in __post_init__
    if dart.band == DartBand.MISS:
        if dart.score != 0:
            raise ValueError("Miss dart must have score 0")
        return
    if dart.band == DartBand.BULL:
        if dart.score != 25:
            raise ValueError("Bull dart must have score 25")
        return
    if dart.band == DartBand.BULLSEYE:
        if dart.score != 50:
            raise ValueError("Bullseye dart must have score 50")
        return
    if dart.band == DartBand.SINGLE:
        if not (1 <= dart.score <= 20):
            raise ValueError(f"Single dart score must be 1–20, got {dart.score}")
        return
    if dart.band == DartBand.DOUBLE:
        if not (dart.score % 2 == 0 and 1 <= dart.score // 2 <= 20):
            raise ValueError(f"Invalid double dart score {dart.score}")
        return
    if dart.band == DartBand.TRIPLE:
        if not (dart.score % 3 == 0 and 1 <= dart.score // 3 <= 20):
            raise ValueError(f"Invalid triple dart score {dart.score}")
        return


# ---------------------------------------------------------------------------
# Bull throw
# ---------------------------------------------------------------------------


@dataclass
class BullThrowResult:
    """Bull-throw outcome — full playing order for a match.

    play_order contains player IDs in the order they will throw during the leg.
    - Singles: [first_player_id, second_player_id]
    - Doubles: [p_best, p_best_opponent, p_partner_of_best, p_remaining]
    """

    play_order: list[int]


def record_singles_bull_throw(
    player1_id: int,
    player2_id: int,
    winner_id: int,
) -> BullThrowResult:
    """Record the result of a singles bull throw.

    The referee simply selects which player threw closer to the bull.
    No distance measurement is needed.

    winner_id must be either player1_id or player2_id.
    """
    if winner_id == player1_id:
        return BullThrowResult(play_order=[player1_id, player2_id])
    if winner_id == player2_id:
        return BullThrowResult(play_order=[player2_id, player1_id])
    raise ValueError(
        f"winner_id {winner_id} is not one of the match players "
        f"({player1_id}, {player2_id})"
    )


def record_doubles_bull_throw(
    team1: tuple[int, int],
    team2: tuple[int, int],
    best_player_id: int,
    best_opponent_id: int,
) -> BullThrowResult:
    """Determine playing order for a doubles match from bull throws.

    All 4 players throw. The referee identifies:
    - best_player_id:   the player with the best (closest) throw overall
    - best_opponent_id: the best thrower from the *opposing* team

    Playing order:
      1. best_player_id
      2. best_opponent_id
      3. partner of best_player_id (the other member of their team)
      4. remaining opponent

    Args:
        team1:            (player1_id, player2_id)
        team2:            (player3_id, player4_id)
        best_player_id:   must be in team1 or team2
        best_opponent_id: must be in the team that does NOT contain best_player_id
    """
    all_players = set(team1) | set(team2)
    if best_player_id not in all_players:
        raise ValueError(f"best_player_id {best_player_id} not in match")
    if best_opponent_id not in all_players:
        raise ValueError(f"best_opponent_id {best_opponent_id} not in match")

    best_team = team1 if best_player_id in team1 else team2
    opp_team = team2 if best_player_id in team1 else team1

    if best_opponent_id not in opp_team:
        raise ValueError(
            f"best_opponent_id {best_opponent_id} must be from the opposing team"
        )

    partner = next(p for p in best_team if p != best_player_id)
    remaining = next(p for p in opp_team if p != best_opponent_id)

    return BullThrowResult(
        play_order=[best_player_id, best_opponent_id, partner, remaining]
    )


# ---------------------------------------------------------------------------
# Visit / score entry
# ---------------------------------------------------------------------------


@dataclass
class VisitResult:
    """Outcome of processing one visit (3 darts)."""

    darts: list[Dart]          # exactly 3 darts
    total: int                  # score actually counted (0 if bust)
    is_bust: bool
    remaining_after: int        # remaining score after this visit
    finishing_dart: Dart | None  # set if the visit finishes the leg
    single_out_mode: bool       # True if Single-Out rules were active


def _compute_valid_score(darts: list[Dart]) -> int:
    return sum(d.score for d in darts)


def _is_double_out_finish(dart: Dart) -> bool:
    """True if this dart constitutes a valid Double-Out finish."""
    return dart.is_double or dart.is_bullseye


def process_visit(
    darts: list[Dart],
    remaining: int,
    visit_number: int,
    single_out_mode: bool,
) -> VisitResult:
    """Process a 3-dart visit and return the result.

    Args:
        darts:           Exactly 3 Dart objects.
        remaining:       Score remaining at the start of this visit.
        visit_number:    1-based visit index for this player in this leg (used for
                         Single-Out fallback threshold determination externally;
                         here used only for documentation purposes).
        single_out_mode: If True, player may finish on any field (no double required).
    """
    if len(darts) != 3:
        raise ValueError("A visit must contain exactly 3 darts")

    for d in darts:
        validate_dart(d)

    total = _compute_valid_score(darts)

    # --- Bust detection ---
    new_remaining = remaining - total

    if new_remaining < 0:
        # Overshot — bust
        return VisitResult(
            darts=darts,
            total=0,
            is_bust=True,
            remaining_after=remaining,
            finishing_dart=None,
            single_out_mode=single_out_mode,
        )

    if new_remaining == 1 and not single_out_mode:
        # Can't finish on 1 in Double-Out (no double worth 1 exists)
        return VisitResult(
            darts=darts,
            total=0,
            is_bust=True,
            remaining_after=remaining,
            finishing_dart=None,
            single_out_mode=single_out_mode,
        )

    if new_remaining == 0:
        # Potential finish — check out rule
        finishing_dart = _find_finishing_dart(darts, remaining)
        if not single_out_mode and not _is_double_out_finish(finishing_dart):
            # Final dart was not a double → bust
            return VisitResult(
                darts=darts,
                total=0,
                is_bust=True,
                remaining_after=remaining,
                finishing_dart=None,
                single_out_mode=single_out_mode,
            )
        # Valid finish
        return VisitResult(
            darts=darts,
            total=total,
            is_bust=False,
            remaining_after=0,
            finishing_dart=finishing_dart,
            single_out_mode=single_out_mode,
        )

    # Normal visit — no finish, no bust
    return VisitResult(
        darts=darts,
        total=total,
        is_bust=False,
        remaining_after=new_remaining,
        finishing_dart=None,
        single_out_mode=single_out_mode,
    )


def _find_finishing_dart(darts: list[Dart], remaining: int) -> Dart:
    """Find the dart that reduced remaining to 0.

    We scan darts from left to right; once the running total equals remaining,
    that dart is the finishing dart.  (Darts after the finishing dart scored 0.)
    """
    running = 0
    for dart in darts:
        running += dart.score
        if running == remaining:
            return dart
    # Fallback — should not happen if total == remaining
    return darts[-1]


# ---------------------------------------------------------------------------
# Single-Out fallback
# ---------------------------------------------------------------------------


def should_switch_to_single_out(
    visit_number: int,
    round_type: str,
) -> bool:
    """Return True if visit_number exceeds the Single-Out threshold for round_type.

    round_type: "vorrunde" | "ko" | "lightning"
    Lightning Round is already Single-Out from the start, so this always
    returns False for lightning (threshold never applies).
    """
    if round_type == "lightning":
        return False  # Lightning is always Single-Out
    threshold = (
        VORRUNDE_SINGLE_OUT_VISIT if round_type == "vorrunde" else KO_SINGLE_OUT_VISIT
    )
    return visit_number > threshold


# ---------------------------------------------------------------------------
# Checkout suggestion engine
# ---------------------------------------------------------------------------

# Dartboard single-field values
_SINGLES = list(range(1, 21)) + [25]
# Double-field values (D1=2 … D20=40, D25=50)
_DOUBLES = [n * 2 for n in range(1, 21)] + [50]
# Triple-field values (T1=3 … T20=60)
_TRIPLES = [n * 3 for n in range(1, 21)]

# All possible single-dart scores (miss excluded)
_ALL_SCORES = sorted(set(_SINGLES + _DOUBLES + _TRIPLES))


def _dart_label(score: int) -> str:
    """Human-readable dart label: S20, D20, T20, Bull, Bullseye."""
    if score == 50:
        return "Bullseye"
    if score == 25:
        return "Bull"
    if score % 3 == 0 and 1 <= score // 3 <= 20:
        return f"T{score // 3}"
    if score % 2 == 0 and 1 <= score // 2 <= 20:
        return f"D{score // 2}"
    if 1 <= score <= 20:
        return f"S{score}"
    return str(score)


def _is_finish_dart(score: int) -> bool:
    """True if this score can be a valid Double-Out finishing dart."""
    return score in _DOUBLES  # includes 50 (Bullseye)


def _finish_label(score: int) -> str:
    """Return the correct label for a finishing double dart.

    Unlike _dart_label, this always renders the score as a double field
    (e.g. 6 → D3, never T2), since only doubles are valid finishes.
    """
    if score == 50:
        return "Bullseye"
    return f"D{score // 2}"


def _build_checkout_table() -> dict[int, list[str]]:
    """Precompute optimal 1-, 2-, or 3-dart checkout paths for scores 2–170.

    Returns a dict mapping remaining_score → list of dart labels
    (e.g. ["T20", "T20", "D20"]) or an empty list if no checkout exists in ≤ 3 darts.

    Strategy: shortest path first (1-dart, then 2-dart, then 3-dart).
    Among equal-length paths, prefer higher first dart to deplete score quickly.
    """
    table: dict[int, list[str]] = {}

    for target in range(2, 171):
        path = _find_checkout(target)
        table[target] = path

    return table


def _find_checkout(target: int) -> list[str]:
    """Find the shortest checkout path for *target* (Double-Out, ≤3 darts)."""
    # 1-dart finish
    if target in _DOUBLES:
        return [_finish_label(target)]

    # 2-dart finish: first dart (any) + finishing double
    # Try highest first darts first for efficiency
    for first in sorted(_ALL_SCORES, reverse=True):
        remainder = target - first
        if remainder in _DOUBLES and remainder >= 2:
            return [_dart_label(first), _finish_label(remainder)]

    # 3-dart finish
    for first in sorted(_ALL_SCORES, reverse=True):
        r1 = target - first
        if r1 < 2:
            continue
        for second in sorted(_ALL_SCORES, reverse=True):
            remainder = r1 - second
            if remainder in _DOUBLES and remainder >= 2:
                return [
                    _dart_label(first),
                    _dart_label(second),
                    _finish_label(remainder),
                ]

    return []  # no checkout possible in ≤3 darts


# Build the table once at import time
_CHECKOUT_TABLE: dict[int, list[str]] = _build_checkout_table()


def get_checkout_suggestion(remaining: int) -> list[str]:
    """Return the optimal checkout path for *remaining* score.

    Returns a list of dart labels (1–3 elements) or an empty list if no
    checkout is possible in ≤3 darts (e.g. remaining > 170 or remaining == 1).
    """
    if remaining < 2 or remaining > 170:
        return []
    return _CHECKOUT_TABLE.get(remaining, [])
