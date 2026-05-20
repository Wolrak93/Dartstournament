"""Handicap calculator for the Backsberger Open.

Rules:
- Singles: compare championship counts of both players.
  If |A - B| >= 3, the stronger player's starting score is increased by
  100 + (diff - 3) * 40 points (e.g. diff=3 → +100, diff=4 → +140).
- Doubles (2v2): four pairwise comparisons are made
  (team1_p1 vs team2_p1, team1_p1 vs team2_p2,
   team1_p2 vs team2_p1, team1_p2 vs team2_p2).
  Handicap values are summed per team, then divided by 4 and rounded.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HANDICAP_THRESHOLD: int = 3  # minimum difference before handicap applies
_HANDICAP_BASE: int = 100  # extra points for diff == threshold
_HANDICAP_STEP: int = 40  # extra points per additional championship beyond threshold


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HandicapResult:
    """Starting scores for both sides after applying the handicap."""

    starting_score_a: int  # player A / team 1
    starting_score_b: int  # player B / team 2


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _raw_handicap(champ_a: int, champ_b: int) -> int:
    """Return the extra starting points that apply to the stronger side.

    Returns 0 if the difference is below the threshold.
    """
    diff = abs(champ_a - champ_b)
    if diff < _HANDICAP_THRESHOLD:
        return 0
    return _HANDICAP_BASE + (diff - _HANDICAP_THRESHOLD) * _HANDICAP_STEP


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_singles_handicap(
    champ_a: int,
    champ_b: int,
    base_score: int,
) -> HandicapResult:
    """Compute adjusted starting scores for a singles match.

    The stronger player (higher championship count) receives the handicap,
    meaning their starting score is raised so they have more points to play down.

    Args:
        champ_a: Championship count of player A.
        champ_b: Championship count of player B.
        base_score: Base starting score (e.g. 301 for Vorrunde, 501 for KO).

    Returns:
        HandicapResult with (starting_score_a, starting_score_b).
    """
    extra = _raw_handicap(champ_a, champ_b)
    if champ_a > champ_b:
        return HandicapResult(base_score + extra, base_score)
    if champ_b > champ_a:
        return HandicapResult(base_score, base_score + extra)
    return HandicapResult(base_score, base_score)


def compute_doubles_handicap(
    champ_p1: int,
    champ_p2: int,
    champ_p3: int,
    champ_p4: int,
    base_score: int,
) -> HandicapResult:
    """Compute adjusted starting scores for a doubles match.

    Team 1 = (p1, p2), Team 2 = (p3, p4).

    Four pairwise comparisons are evaluated:
        p1 vs p3, p1 vs p4, p2 vs p3, p2 vs p4.
    For each comparison the handicap value is assigned to the team whose
    player is stronger (higher championships).  All values per team are
    summed, then divided by 4 and rounded to the nearest integer.

    Args:
        champ_p1: Championships of team-1 player 1.
        champ_p2: Championships of team-1 player 2.
        champ_p3: Championships of team-2 player 1.
        champ_p4: Championships of team-2 player 2.
        base_score: Base starting score (e.g. 301 or 501).

    Returns:
        HandicapResult with (starting_score_team1, starting_score_team2).
    """
    comparisons: list[tuple[int, int]] = [
        (champ_p1, champ_p3),
        (champ_p1, champ_p4),
        (champ_p2, champ_p3),
        (champ_p2, champ_p4),
    ]

    team1_total = 0
    team2_total = 0
    for ca, cb in comparisons:
        extra = _raw_handicap(ca, cb)
        if ca > cb:
            team1_total += extra
        elif cb > ca:
            team2_total += extra

    team1_handicap = round(team1_total / 4)
    team2_handicap = round(team2_total / 4)

    return HandicapResult(
        base_score + team1_handicap,
        base_score + team2_handicap,
    )
