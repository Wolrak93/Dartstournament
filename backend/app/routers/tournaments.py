"""Tournament endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import bad_request, conflict, not_found
from app.models.match import MatchStatus, RoundType
from app.models.tournament import TournamentMode, TournamentStatus
from app.repositories.match_repo import (
    create_match,
    list_matches_by_tournament,
)
from app.repositories.player_repo import get_player_by_id
from app.repositories.tournament_player_repo import (
    add_player_to_tournament,
    list_tournament_players,
)
from app.repositories.tournament_repo import (
    create_tournament,
    get_tournament_by_id,
    update_tournament_status,
)
from app.schemas.match import MatchRead
from app.schemas.tournament import TournamentPlayerRead, TournamentRead
from app.services.handicap import compute_doubles_handicap, compute_singles_handicap
from app.services.vorrunde import (
    PlayerStanding,
    SwissState,
    generate_fixed_draw,
    generate_swiss_round,
    is_doubles_mode,
)

router = APIRouter(prefix="/tournaments", tags=["tournaments"])

VORRUNDE_BASE_SCORE = 301
KO_BASE_SCORE = 501


# ---------------------------------------------------------------------------
# Request / Response schemas local to this module
# ---------------------------------------------------------------------------


class TournamentCreateRequest(BaseModel):
    player_ids: list[int] = Field(..., min_length=9, max_length=13)
    mode: TournamentMode = TournamentMode.swiss


class TournamentDetailRead(BaseModel):
    id: int
    player_count: int
    mode: TournamentMode
    status: TournamentStatus
    players: list[TournamentPlayerRead]


class StandingEntry(BaseModel):
    rank: int
    player_id: int
    reg_points: float
    bonus_points: int
    avg_score: float
    total_points: float


class QualifiedPlayerRead(BaseModel):
    player_id: int
    seed: int
    qualified_via: str


class KOMatchupRead(BaseModel):
    match_id: int
    stage: str
    player1_id: int
    player2_id: int
    starting_score_p1: int
    starting_score_p2: int
    status: MatchStatus
    winner_id: int | None


class KOBracketResponse(BaseModel):
    qualified_players: list[QualifiedPlayerRead]
    quarter_finals: list[KOMatchupRead]
    semi_finals: list[KOMatchupRead]
    final: KOMatchupRead | None
    third_place: KOMatchupRead | None
    lightning_player_ids: list[int]


class LightningMatchRead(BaseModel):
    match_id: int
    round_number: int
    player1_id: int
    player2_id: int
    status: MatchStatus
    winner_id: int | None


class LightningResponse(BaseModel):
    matches: list[LightningMatchRead]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ko_stage_from_round(round_number: int, total_rounds: int) -> str:
    """Map a KO round_number to its stage label.

    Convention used when persisting KO matches:
      round 1 = qf (quarter-finals)
      round 2 = sf (semi-finals)
      round 3 = final + third_place
    """
    if round_number == 1:
        return "qf"
    if round_number == 2:
        return "sf"
    return "final"  # round 3: final and third_place both stored here


async def _get_tournament_or_404(db: AsyncSession, tournament_id: int):
    tournament = await get_tournament_by_id(db, tournament_id)
    if tournament is None:
        raise not_found("Tournament", tournament_id)
    return tournament


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=TournamentRead, status_code=201)
async def create_new_tournament(
    body: TournamentCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> TournamentRead:
    # Validate all player IDs exist
    for pid in body.player_ids:
        player = await get_player_by_id(db, pid)
        if player is None:
            raise not_found("Player", pid)

    # Reject duplicate player IDs
    if len(set(body.player_ids)) != len(body.player_ids):
        raise bad_request("Duplicate player IDs in request.", "duplicate_player_ids")

    tournament = await create_tournament(
        db, player_count=len(body.player_ids), mode=body.mode
    )
    for pid in body.player_ids:
        await add_player_to_tournament(db, tournament_id=tournament.id, player_id=pid)

    await db.commit()
    await db.refresh(tournament)
    return TournamentRead.model_validate(tournament)


@router.get("/{tournament_id}", response_model=TournamentDetailRead)
async def get_tournament(
    tournament_id: int,
    db: AsyncSession = Depends(get_db),
) -> TournamentDetailRead:
    tournament = await _get_tournament_or_404(db, tournament_id)
    players = await list_tournament_players(db, tournament_id)
    return TournamentDetailRead(
        id=tournament.id,
        player_count=tournament.player_count,
        mode=tournament.mode,
        status=tournament.status,
        players=[TournamentPlayerRead.model_validate(tp) for tp in players],
    )


@router.post("/{tournament_id}/start", response_model=list[MatchRead], status_code=201)
async def start_tournament(
    tournament_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[MatchRead]:
    tournament = await _get_tournament_or_404(db, tournament_id)

    if tournament.status != TournamentStatus.pending:
        raise conflict(
            f"Tournament is already in status '{tournament.status}'; cannot start.",
            "tournament_already_started",
        )

    # Load registered players and their championship counts
    tp_rows = await list_tournament_players(db, tournament_id)
    if len(tp_rows) != tournament.player_count:
        raise conflict(
            "Registered player count does not match tournament player_count.",
            "player_count_mismatch",
        )

    player_ids = [tp.player_id for tp in tp_rows]
    champ_counts: dict[int, int] = {}
    for pid in player_ids:
        p = await get_player_by_id(db, pid)
        champ_counts[pid] = p.championship_count if p else 0

    doubles = is_doubles_mode(len(player_ids))
    base_score = VORRUNDE_BASE_SCORE

    # Generate schedule
    if tournament.mode == TournamentMode.fixed:
        pairings = generate_fixed_draw(player_ids)
    else:
        # Swiss: generate only round 1
        state = SwissState(player_ids=player_ids)
        pairings = generate_swiss_round(state)

    created_matches = []
    for pairing in pairings:
        if doubles:
            # team1 = [p1, p3], team2 = [p2, p4]
            p1, p3 = pairing.team1[0], pairing.team1[1]
            p2, p4 = pairing.team2[0], pairing.team2[1]
            result = compute_doubles_handicap(
                champ_counts.get(p1, 0),
                champ_counts.get(p3, 0),
                champ_counts.get(p2, 0),
                champ_counts.get(p4, 0),
                base_score,
            )
            match = await create_match(
                db,
                tournament_id=tournament_id,
                round_type=RoundType.vorrunde,
                round_number=pairing.round_number,
                player1_id=p1,
                player2_id=p2,
                player3_id=p3,
                player4_id=p4,
                starting_score_p1=result.starting_score_a,
                starting_score_p2=result.starting_score_b,
            )
        else:
            p1 = pairing.team1[0]
            p2 = pairing.team2[0]
            result = compute_singles_handicap(
                champ_counts.get(p1, 0),
                champ_counts.get(p2, 0),
                base_score,
            )
            match = await create_match(
                db,
                tournament_id=tournament_id,
                round_type=RoundType.vorrunde,
                round_number=pairing.round_number,
                player1_id=p1,
                player2_id=p2,
                starting_score_p1=result.starting_score_a,
                starting_score_p2=result.starting_score_b,
            )
        created_matches.append(match)

    await update_tournament_status(db, tournament_id, TournamentStatus.vorrunde)
    await db.commit()

    for m in created_matches:
        await db.refresh(m)
    return [MatchRead.model_validate(m) for m in created_matches]


@router.get("/{tournament_id}/standings", response_model=list[StandingEntry])
async def get_standings(
    tournament_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[StandingEntry]:
    await _get_tournament_or_404(db, tournament_id)
    tp_rows = await list_tournament_players(db, tournament_id)

    standings = []
    for tp in tp_rows:
        standings.append(
            PlayerStanding(
                player_id=tp.player_id,
                reg_points=tp.reg_points,
                bonus_points=tp.bonus_points,
                total_score=round(tp.avg_score * 100),
                total_visits=100 if tp.avg_score > 0 else 0,
            )
        )

    standings.sort(
        key=lambda s: (s.reg_points + s.avg_bonus, s.bonus_points),
        reverse=True,
    )

    return [
        StandingEntry(
            rank=idx + 1,
            player_id=s.player_id,
            reg_points=s.reg_points,
            bonus_points=s.bonus_points,
            avg_score=s.avg_score,
            total_points=s.reg_points + s.avg_bonus,
        )
        for idx, s in enumerate(standings)
    ]


@router.get("/{tournament_id}/matches", response_model=list[MatchRead])
async def get_matches(
    tournament_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[MatchRead]:
    await _get_tournament_or_404(db, tournament_id)
    matches = await list_matches_by_tournament(db, tournament_id)
    return [MatchRead.model_validate(m) for m in matches]


@router.get("/{tournament_id}/matches/next", response_model=list[MatchRead])
async def get_next_matches(
    tournament_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[MatchRead]:
    await _get_tournament_or_404(db, tournament_id)
    all_matches = await list_matches_by_tournament(db, tournament_id)
    pending = [m for m in all_matches if m.status == MatchStatus.pending]
    # Return the first pending match(es) from the lowest round number
    if not pending:
        return []
    min_round = min(m.round_number for m in pending)
    return [MatchRead.model_validate(m) for m in pending if m.round_number == min_round]


@router.post(
    "/{tournament_id}/ko/start", response_model=KOBracketResponse, status_code=201
)
async def start_ko_phase(
    tournament_id: int,
    db: AsyncSession = Depends(get_db),
) -> KOBracketResponse:
    from app.services.ko import generate_ko_bracket

    tournament = await _get_tournament_or_404(db, tournament_id)

    if tournament.status != TournamentStatus.vorrunde:
        raise conflict(
            f"KO phase can only start when tournament is in 'vorrunde' status, "
            f"currently '{tournament.status}'.",
            "invalid_tournament_status",
        )

    tp_rows = await list_tournament_players(db, tournament_id)

    # Rebuild PlayerStanding objects from stored standings
    player_standings: list[PlayerStanding] = []
    champ_counts: dict[int, int] = {}
    for tp in tp_rows:
        p = await get_player_by_id(db, tp.player_id)
        champ_counts[tp.player_id] = p.championship_count if p else 0
        player_standings.append(
            PlayerStanding(
                player_id=tp.player_id,
                reg_points=tp.reg_points,
                bonus_points=tp.bonus_points,
                total_score=round(tp.avg_score * 100),
                total_visits=100 if tp.avg_score > 0 else 0,
            )
        )

    bracket = generate_ko_bracket(player_standings, champ_counts)

    # Persist QF matches
    ko_matches: list[MatchRead] = []
    for mu in bracket.qf_matches:
        match = await create_match(
            db,
            tournament_id=tournament_id,
            round_type=RoundType.ko,
            round_number=1,  # QF = round 1
            player1_id=mu.player1_id,
            player2_id=mu.player2_id,
            starting_score_p1=mu.starting_score_p1,
            starting_score_p2=mu.starting_score_p2,
        )
        ko_matches.append(match)

    # Non-qualifiers → Lightning Round pool (no matches yet; scheduled after QF)
    qualified_ids = {q.player_id for q in bracket.seeding}
    lightning_ids = [
        tp.player_id for tp in tp_rows if tp.player_id not in qualified_ids
    ]

    await update_tournament_status(db, tournament_id, TournamentStatus.ko)
    await db.commit()

    for m in ko_matches:
        await db.refresh(m)

    qf_reads = [
        KOMatchupRead(
            match_id=m.id,
            stage="qf",
            player1_id=m.player1_id,
            player2_id=m.player2_id,
            starting_score_p1=m.starting_score_p1,
            starting_score_p2=m.starting_score_p2,
            status=m.status,
            winner_id=m.winner_id,
        )
        for m in ko_matches
    ]

    return KOBracketResponse(
        qualified_players=[
            QualifiedPlayerRead(
                player_id=q.player_id,
                seed=q.seed,
                qualified_via=q.qualified_via,
            )
            for q in bracket.seeding
        ],
        quarter_finals=qf_reads,
        semi_finals=[],
        final=None,
        third_place=None,
        lightning_player_ids=lightning_ids,
    )


@router.get("/{tournament_id}/ko/bracket", response_model=KOBracketResponse)
async def get_ko_bracket(
    tournament_id: int,
    db: AsyncSession = Depends(get_db),
) -> KOBracketResponse:
    tournament = await _get_tournament_or_404(db, tournament_id)

    if tournament.status not in (TournamentStatus.ko, TournamentStatus.finished):
        raise conflict(
            "KO bracket is only available once the KO phase has started.",
            "ko_not_started",
        )

    all_matches = await list_matches_by_tournament(db, tournament_id)
    ko_matches = [m for m in all_matches if m.round_type == RoundType.ko]

    def _to_read(m, stage: str) -> KOMatchupRead:
        return KOMatchupRead(
            match_id=m.id,
            stage=stage,
            player1_id=m.player1_id,
            player2_id=m.player2_id,
            starting_score_p1=m.starting_score_p1,
            starting_score_p2=m.starting_score_p2,
            status=m.status,
            winner_id=m.winner_id,
        )

    qf = [_to_read(m, "qf") for m in ko_matches if m.round_number == 1]
    sf = [_to_read(m, "sf") for m in ko_matches if m.round_number == 2]
    r3 = [m for m in ko_matches if m.round_number == 3]
    final = _to_read(r3[0], "final") if len(r3) >= 1 else None
    third = _to_read(r3[1], "third_place") if len(r3) >= 2 else None

    # Reconstruct qualified players from QF participants
    qualified: list[QualifiedPlayerRead] = []
    seen: set[int] = set()
    seed = 1
    for m in sorted(ko_matches, key=lambda x: x.id):
        if m.round_number == 1:
            for pid in (m.player1_id, m.player2_id):
                if pid not in seen:
                    qualified.append(
                        QualifiedPlayerRead(
                            player_id=pid, seed=seed, qualified_via="regular"
                        )
                    )
                    seen.add(pid)
                    seed += 1

    # Non-qualified players = all tournament players not in the bracket
    tp_rows = await list_tournament_players(db, tournament_id)
    lightning_ids = [tp.player_id for tp in tp_rows if tp.player_id not in seen]

    return KOBracketResponse(
        qualified_players=qualified,
        quarter_finals=qf,
        semi_finals=sf,
        final=final,
        third_place=third,
        lightning_player_ids=lightning_ids,
    )


@router.get("/{tournament_id}/lightning", response_model=LightningResponse)
async def get_lightning_round(
    tournament_id: int,
    db: AsyncSession = Depends(get_db),
) -> LightningResponse:
    await _get_tournament_or_404(db, tournament_id)
    all_matches = await list_matches_by_tournament(db, tournament_id)
    lightning = [m for m in all_matches if m.round_type == RoundType.lightning]
    return LightningResponse(
        matches=[
            LightningMatchRead(
                match_id=m.id,
                round_number=m.round_number,
                player1_id=m.player1_id,
                player2_id=m.player2_id,
                status=m.status,
                winner_id=m.winner_id,
            )
            for m in lightning
        ]
    )
