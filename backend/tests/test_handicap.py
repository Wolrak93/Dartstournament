"""Tests for the handicap calculator (Task 7)."""

from app.services.handicap import (
    HandicapResult,
    compute_doubles_handicap,
    compute_singles_handicap,
)

# ---------------------------------------------------------------------------
# Singles — no handicap cases
# ---------------------------------------------------------------------------


def test_singles_no_handicap_equal_championships():
    result = compute_singles_handicap(2, 2, 301)
    assert result == HandicapResult(301, 301)


def test_singles_no_handicap_diff_0():
    result = compute_singles_handicap(0, 0, 301)
    assert result == HandicapResult(301, 301)


def test_singles_no_handicap_diff_1():
    result = compute_singles_handicap(1, 0, 301)
    assert result == HandicapResult(301, 301)


def test_singles_no_handicap_diff_2():
    result = compute_singles_handicap(5, 3, 301)  # diff = 2
    assert result == HandicapResult(301, 301)


# ---------------------------------------------------------------------------
# Singles — handicap applies
# ---------------------------------------------------------------------------


def test_singles_handicap_diff_3_a_stronger():
    # diff=3 → extra = 100 + (3-3)*40 = 100
    result = compute_singles_handicap(5, 2, 301)
    assert result == HandicapResult(401, 301)


def test_singles_handicap_diff_3_b_stronger():
    result = compute_singles_handicap(0, 3, 301)
    assert result == HandicapResult(301, 401)


def test_singles_handicap_diff_4():
    # diff=4 → extra = 100 + (4-3)*40 = 140
    result = compute_singles_handicap(4, 0, 301)
    assert result == HandicapResult(441, 301)


def test_singles_handicap_diff_5():
    # diff=5 → extra = 100 + (5-3)*40 = 180
    result = compute_singles_handicap(5, 0, 301)
    assert result == HandicapResult(481, 301)


def test_singles_handicap_ko_base_501():
    # diff=3, base=501 → stronger player starts at 601
    result = compute_singles_handicap(3, 0, 501)
    assert result == HandicapResult(601, 501)


def test_singles_handicap_large_diff():
    # diff=8 → extra = 100 + (8-3)*40 = 300
    result = compute_singles_handicap(8, 0, 301)
    assert result == HandicapResult(601, 301)


# ---------------------------------------------------------------------------
# Doubles — no handicap
# ---------------------------------------------------------------------------


def test_doubles_no_handicap_all_equal():
    result = compute_doubles_handicap(2, 2, 2, 2, 301)
    assert result == HandicapResult(301, 301)


def test_doubles_no_handicap_small_diffs():
    # All pairwise diffs < 3
    result = compute_doubles_handicap(2, 1, 2, 1, 301)
    assert result == HandicapResult(301, 301)


# ---------------------------------------------------------------------------
# Doubles — handicap applies
# ---------------------------------------------------------------------------


def test_doubles_one_strong_player_on_team1():
    # p1=5, p2=0, p3=0, p4=0
    # p1 vs p3: diff=5 → 180, team1
    # p1 vs p4: diff=5 → 180, team1
    # p2 vs p3: diff=0 → 0
    # p2 vs p4: diff=0 → 0
    # team1_total=360 → round(360/4)=90
    result = compute_doubles_handicap(5, 0, 0, 0, 301)
    assert result == HandicapResult(391, 301)


def test_doubles_symmetric_strong_players():
    # p1=5, p2=0, p3=5, p4=0
    # p1 vs p3: diff=0 → 0
    # p1 vs p4: diff=5 → 180, team1
    # p2 vs p3: diff=5 → 180, team2
    # p2 vs p4: diff=0 → 0
    # team1=180 → round(180/4)=45; team2=180 → 45
    result = compute_doubles_handicap(5, 0, 5, 0, 301)
    assert result == HandicapResult(346, 346)


def test_doubles_threshold_boundary():
    # p1=3, p2=0, p3=0, p4=0
    # p1 vs p3: diff=3 → 100, team1
    # p1 vs p4: diff=3 → 100, team1
    # others: 0
    # team1_total=200 → round(200/4)=50
    result = compute_doubles_handicap(3, 0, 0, 0, 301)
    assert result == HandicapResult(351, 301)


def test_doubles_team2_dominant():
    # p1=0, p2=0, p3=4, p4=4
    # p1 vs p3: diff=4 → 140, team2
    # p1 vs p4: diff=4 → 140, team2
    # p2 vs p3: diff=4 → 140, team2
    # p2 vs p4: diff=4 → 140, team2
    # team2_total=560 → round(560/4)=140
    result = compute_doubles_handicap(0, 0, 4, 4, 301)
    assert result == HandicapResult(301, 441)


def test_doubles_rounding_up():
    # p1=6, p2=0, p3=0, p4=0
    # diff(p1,p3)=6 → 100+(6-3)*40=220, team1
    # diff(p1,p4)=6 → 220, team1
    # others: 0
    # team1_total=440 → round(440/4)=110
    result = compute_doubles_handicap(6, 0, 0, 0, 301)
    assert result == HandicapResult(411, 301)


def test_doubles_base_score_501():
    # diff=3 on all 4 comparisons for team1 players
    # p1=3, p2=3, p3=0, p4=0
    # p1 vs p3: diff=3 → 100, team1
    # p1 vs p4: diff=3 → 100, team1
    # p2 vs p3: diff=3 → 100, team1
    # p2 vs p4: diff=3 → 100, team1
    # team1_total=400 → round(400/4)=100
    result = compute_doubles_handicap(3, 3, 0, 0, 501)
    assert result == HandicapResult(601, 501)
