"""Match flow engine for the Backsberger Open.

Handles:
- Bull throw (closest to bull determines who goes first; tie → re-throw)
- Score entry and validation per visit (dart1, dart2, dart3)
- Bust detection (Double-Out and Single-Out rules)
- Single-Out fallback after visit limit (15 Vorrunde / 25 KO)
- Checkout suggestions for remaining scores 2–170 (Double-Out),
  171–230 (setup shots), and 1–180 (Single-Out)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

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

# Dartboard field values
_SINGLES = list(range(1, 21)) + [25]
_DOUBLES = [n * 2 for n in range(1, 21)] + [50]
_TRIPLES = [n * 3 for n in range(1, 21)]
_ALL_SCORES = sorted(set(_SINGLES + _DOUBLES + _TRIPLES))
_ALL_SCORES_DESC = sorted(_ALL_SCORES, reverse=True)

# Path to the pre-computed Double-Out lookup table (JSON)
_DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class CheckoutSuggestion:
    """A checkout suggestion displayed to the referee.

    darts    - 1–3 dart labels (e.g. ["T20", "T20", "D20"])
    is_finish - True if throwing these darts would finish the leg
    leave    - remaining score after throwing all darts; 0 when is_finish
    text     - raw display string as read from the checkout table
    """

    darts: list[str]
    is_finish: bool
    leave: int
    text: str


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
        return str(score)
    return str(score)


def _finish_label(score: int) -> str:
    """Return the correct label for a finishing double dart.

    Unlike _dart_label, this always renders the score as a double field
    (e.g. 6 → D3, never T2), since only doubles are valid finishes.
    """
    if score == 50:
        return "Bullseye"
    return f"D{score // 2}"


def _token_score(token: str) -> int | None:
    """Numeric score for a JSON table token (e.g. 'T20' → 60, 'B' → 25)."""
    t = token.strip()
    if t == "BE":
        return 50
    if t == "B":
        return 25
    if t.startswith("T") and len(t) > 1:
        try:
            return int(t[1:]) * 3
        except ValueError:
            return None
    if t.startswith("D") and len(t) > 1:
        try:
            return int(t[1:]) * 2
        except ValueError:
            return None
    if t.startswith("S") and len(t) > 1:
        try:
            return int(t[1:])
        except ValueError:
            return None
    try:
        return int(t)
    except ValueError:
        return None


def _token_label(token: str) -> str:
    """Normalize a JSON table token to a display label."""
    t = token.strip()
    if t == "BE":
        return "Bullseye"
    if t == "B":
        return "Bull"
    if t.startswith(("T", "D", "S")):
        return t
    # Bare integer in JSON = single field
    try:
        n = int(t)
        return f"S{n}"
    except ValueError:
        return t


def _parse_checkout_path(
    path_str: str, target: int
) -> CheckoutSuggestion | None:
    """Parse a JSON checkout path string into a CheckoutSuggestion.

    Examples:
        "T20 D20"           → finish path  → darts=["T20", "D20"], is_finish=True
        "No Finish"          → no suggestion  → None
        "No Finish (T20)"   → setup shot   → darts=["T20"], is_finish=False
        "D20 D20 D20 :D"    → finish (easter-egg stripped)
    """
    path_str = re.sub(r"\s*:D\s*", "", path_str).strip()

    if not path_str:
        return None

    if path_str == "No Finish":
        return CheckoutSuggestion(darts=[], is_finish=False, leave=-1, text="No Finish")

    # Setup shot hint: "No Finish (X)"
    m = re.match(r"^No Finish \((.+)\)$", path_str)
    if m:
        token = m.group(1)
        val = _token_score(token)
        if val is not None:
            leave = target - val
            if leave >= 0:
                return CheckoutSuggestion(
                    darts=[_token_label(token)],
                    is_finish=False,
                    leave=leave,
                    text=path_str,
                )
        return None

    # Finish path
    tokens = path_str.split()
    return CheckoutSuggestion(
        darts=[_token_label(t) for t in tokens],
        is_finish=True,
        leave=0,
        text=path_str,
    )


def _load_double_out_table() -> dict[int, tuple[str, str, str]]:
    """Load the Double-Out checkout table from JSON.

    Returns {score: (path_3dart, path_2dart, path_1dart)}.
    Each path is a raw string from the lookup table (e.g. "T20 D20").
    """
    data_file = _DATA_DIR / "double_out_checkouts.json"
    with data_file.open(encoding="utf-8") as f:
        entries = json.load(f)
    table: dict[int, tuple[str, str, str]] = {}
    for entry in entries:
        score = int(entry[3])
        if score >= 2:
            table[score] = (str(entry[0]), str(entry[1]), str(entry[2]))
    return table


# Double-Out lookup: {score: (3-dart path, 2-dart path, 1-dart path)}
_DOUBLE_OUT_TABLE: dict[int, tuple[str, str, str]] = _load_double_out_table()


def _load_single_out_table() -> dict[int, tuple[str, str, str]]:
    """Load the Single-Out checkout table from JSON.

    Returns {score: (path_3dart, path_2dart, path_1dart)}.
    Each path is a raw string from the lookup table (e.g. "T20 T20").
    """
    data_file = _DATA_DIR / "single_out_checkouts.json"
    with data_file.open(encoding="utf-8") as f:
        entries = json.load(f)
    table: dict[int, tuple[str, str, str]] = {}
    for entry in entries:
        score = int(entry[3])
        if score >= 1:
            table[score] = (str(entry[0]), str(entry[1]), str(entry[2]))
    return table


# Single-Out lookup: {score: (3-dart path, 2-dart path, 1-dart path)}
_SINGLE_OUT_TABLE: dict[int, tuple[str, str, str]] = _load_single_out_table()


# ---------------------------------------------------------------------------
# Double-Out checkout suggestion (scores 2–170 via table; 171–230 algorithmic)
# ---------------------------------------------------------------------------


def _double_out_suggestion(
    remaining: int,
    darts_remaining: int,
) -> CheckoutSuggestion | None:
    """Double-Out checkout suggestion for remaining score."""
    if remaining < 2 or remaining > 230:
        return None

    entry = _DOUBLE_OUT_TABLE.get(remaining)
    if not entry:
        return None
    # entry index: 3-dart=0, 2-dart=1, 1-dart=2
    dart_idx = 3 - min(3, max(1, darts_remaining))
    return _parse_checkout_path(entry[dart_idx], remaining)


def _high_score_double_out_setup(
    remaining: int,
    darts_remaining: int,
) -> CheckoutSuggestion | None:
    """Compute setup-shot suggestion for remaining > 170 (up to 230).

    Greedily selects darts to reduce remaining towards a checkable score.
    """
    darts_remaining = min(3, max(1, darts_remaining))

    if darts_remaining == 1:
        # Find dart that leaves the highest checkable score (≤170, non-bogey)
        for score in _ALL_SCORES_DESC:
            leave = remaining - score
            if leave < 2:
                continue
            if leave <= 170:
                entry = _DOUBLE_OUT_TABLE.get(leave)
                if entry and not entry[0].startswith("No Finish"):
                    return CheckoutSuggestion(
                        darts=[_dart_label(score)],
                        is_finish=False,
                        leave=leave,
                    )
        # Fallback: just take the highest shot that leaves ≥ 2
        for score in _ALL_SCORES_DESC:
            leave = remaining - score
            if leave >= 2:
                return CheckoutSuggestion(
                    darts=[_dart_label(score)], is_finish=False, leave=leave
                )
        return None

    if darts_remaining == 2:
        # T20 as first dart; then 1-dart suggestion for what's left
        first_score = 60  # T20
        after = remaining - first_score
        if after >= 2:
            sub = _double_out_suggestion(after, 1)
            if sub:
                return CheckoutSuggestion(
                    darts=["T20"] + sub.darts,
                    is_finish=sub.is_finish,
                    leave=sub.leave,
                )
        return CheckoutSuggestion(
            darts=["T20"], is_finish=False, leave=remaining - first_score
        )

    # darts_remaining == 3: T20 → 2-dart suggestion → extend to 3 darts if needed
    first_score = 60  # T20
    after = remaining - first_score
    if after >= 2:
        sub2 = _double_out_suggestion(after, 2)
        if sub2:
            if len(sub2.darts) >= 2 or sub2.is_finish:
                # sub2 already covers 2 darts (or finishes)
                return CheckoutSuggestion(
                    darts=["T20"] + sub2.darts,
                    is_finish=sub2.is_finish,
                    leave=sub2.leave,
                )
            # sub2 is a 1-dart setup shot; try to extend with a 3rd dart
            sub1 = _double_out_suggestion(sub2.leave, 1) if sub2.leave >= 2 else None
            if sub1:
                return CheckoutSuggestion(
                    darts=["T20"] + sub2.darts + sub1.darts,
                    is_finish=sub1.is_finish,
                    leave=sub1.leave,
                )
            return CheckoutSuggestion(
                darts=["T20"] + sub2.darts,
                is_finish=sub2.is_finish,
                leave=sub2.leave,
            )

    return CheckoutSuggestion(
        darts=["T20", "T20"], is_finish=False, leave=remaining - 120
    )


# ---------------------------------------------------------------------------
# Single-Out checkout suggestion (scores 1–230 via table)
# ---------------------------------------------------------------------------


def _single_out_suggestion(
    remaining: int,
    darts_remaining: int,
) -> CheckoutSuggestion | None:
    """Single-Out checkout suggestion for remaining score (table lookup)."""
    if remaining < 1 or remaining > 230:
        return None

    entry = _SINGLE_OUT_TABLE.get(remaining)
    if not entry:
        return None
    # entry index: 3-dart=0, 2-dart=1, 1-dart=2
    dart_idx = 3 - min(3, max(1, darts_remaining))
    return _parse_checkout_path(entry[dart_idx], remaining)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_checkout_suggestion(
    remaining: int,
    darts_remaining: int = 3,
    single_out: bool = False,
) -> CheckoutSuggestion | None:
    """Return the checkout suggestion for the current remaining score.

    Args:
        remaining:       Current remaining score.
        darts_remaining: How many darts are left to throw this visit (1–3).
        single_out:      If True, any field can finish the leg (no double required).
                         Used for Lightning Round and as fallback after visit limit.

    Returns:
        A CheckoutSuggestion (darts to throw + whether it finishes), or None
        if no suggestion is available (remaining out of display range, etc.).

    Display range:
        Double-Out: 2–230 (finish suggestions up to 170; setup shots 171–230)
        Single-Out: 1–230
    """
    darts_remaining = min(3, max(1, darts_remaining))

    if single_out:
        return _single_out_suggestion(remaining, darts_remaining)
    return _double_out_suggestion(remaining, darts_remaining)


# ---------------------------------------------------------------------------
# Persistence helpers (require an async DB session)
# ---------------------------------------------------------------------------


async def persist_visit(
    db: object,
    match_id: int,
    player_id: int,
    visit_number: int,
    darts: list[Dart],
    result: VisitResult,
    events: list,
) -> object:
    """Persist a single visit and its detected special events to the database.

    Args:
        db:           Async SQLAlchemy session (must be committed by caller).
        match_id:     DB id of the match this visit belongs to.
        player_id:    DB id of the player who threw.
        visit_number: Sequential visit number for this player in this match.
        darts:        List of exactly 3 Dart objects (before bust zeroing).
        result:       VisitResult from process_visit().
        events:       Detected special events from detect_events().

    Returns:
        The newly created Visit ORM object (flushed but not committed).
    """
    from app.repositories.special_event_repo import create_special_event
    from app.repositories.visit_repo import create_visit

    visit = await create_visit(
        db,
        match_id=match_id,
        player_id=player_id,
        visit_number=visit_number,
        dart1=darts[0].score,
        dart2=darts[1].score,
        dart3=darts[2].score,
        total=result.total,
        is_bust=result.is_bust,
    )

    for detected in events:
        await create_special_event(
            db,
            visit_id=visit.id,
            player_id=player_id,
            event_type=detected.event_type,
            bonus_value=detected.bonus_value,
            count=detected.count,
        )

    return visit
