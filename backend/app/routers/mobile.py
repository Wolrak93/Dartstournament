from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_mobile_token, verify_mobile_token
from app.database import get_db
from app.models.match import Match, MatchStatus, RoundType
from app.models.player import Player
from app.models.special_event import SpecialEvent
from app.models.tournament import Tournament, TournamentPlayer, TournamentStatus
from app.schemas.mobile import (
    MobileBracketMatch,
    MobileBracketResponse,
    MobileBracketRound,
    MobileCompletedMatch,
    MobileLiveMatch,
    MobileLoginRequest,
    MobileLoginResponse,
    MobileMatchesResponse,
    MobileNebenrundeMatch,
    MobilePlayerStats,
    MobileProfileResponse,
    MobileStandingEntry,
    MobileStandingsResponse,
    MobileStatsResponse,
    MobileUpcomingMatch,
)

router = APIRouter(prefix="/mobile", tags=["mobile"])
_bearer = HTTPBearer()


async def _get_active_tournament(db: AsyncSession) -> Tournament | None:
    result = await db.execute(
        select(Tournament).where(
            Tournament.status != TournamentStatus.finished
        )
    )
    return result.scalars().first()


async def _get_current_player(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> Player:
    payload = verify_mobile_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        player_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token")
    player = await db.get(Player, player_id)
    if player is None:
        raise HTTPException(status_code=401, detail="Player not found")
    return player


@router.post("/auth/login", response_model=MobileLoginResponse)
async def mobile_login(body: MobileLoginRequest, db: AsyncSession = Depends(get_db)):
    player = await db.get(Player, body.player_id)
    # 4-digit tournament PIN, plaintext acceptable for this use case
    if player is None or player.pin != body.pin:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_mobile_token(player_id=player.id, name=player.name)
    return MobileLoginResponse(token=token, player_id=player.id, name=player.name)


@router.get("/matches", response_model=MobileMatchesResponse)
async def mobile_matches(
    _player: Player = Depends(_get_current_player),
    db: AsyncSession = Depends(get_db),
):
    tournament = await _get_active_tournament(db)
    if tournament is None:
        return MobileMatchesResponse(
            tournament_id=None, live=[], upcoming=[], completed=[]
        )

    players_result = await db.execute(select(Player))
    player_map: dict[int, str] = {p.id: p.name for p in players_result.scalars().all()}

    matches_result = await db.execute(
        select(Match)
        .where(Match.tournament_id == tournament.id)
        .order_by(Match.id)
    )
    matches = matches_result.scalars().all()

    live, upcoming, completed = [], [], []
    for m in matches:
        p1 = player_map.get(m.player1_id, "?")
        p2 = player_map.get(m.player2_id, "?")
        if m.status == MatchStatus.in_progress:
            live.append(MobileLiveMatch(
                match_id=m.id,
                round_type=m.round_type,
                player1_id=m.player1_id,
                player1_name=p1,
                player2_id=m.player2_id,
                player2_name=p2,
            ))
        elif m.status in (MatchStatus.pending, MatchStatus.bull_throw):
            upcoming.append(MobileUpcomingMatch(
                match_id=m.id,
                round_type=m.round_type,
                player1_name=p1,
                player2_name=p2,
            ))
        elif m.status == MatchStatus.finished and m.winner_id is not None:
            completed.append(MobileCompletedMatch(
                match_id=m.id,
                round_type=m.round_type,
                player1_name=p1,
                player2_name=p2,
                winner_name=player_map.get(m.winner_id, "?"),
            ))

    return MobileMatchesResponse(
        tournament_id=tournament.id,
        live=live,
        upcoming=upcoming,
        completed=completed,
    )


@router.get("/standings", response_model=MobileStandingsResponse)
async def mobile_standings(
    _player: Player = Depends(_get_current_player),
    db: AsyncSession = Depends(get_db),
):
    tournament = await _get_active_tournament(db)
    if tournament is None:
        return MobileStandingsResponse(tournament_id=None, phase="none", entries=[])

    result = await db.execute(
        select(TournamentPlayer, Player)
        .join(Player, TournamentPlayer.player_id == Player.id)
        .where(TournamentPlayer.tournament_id == tournament.id)
        .order_by(TournamentPlayer.reg_points.desc())
    )
    rows = result.all()

    entries = []
    for rank, (tp, player) in enumerate(rows, start=1):
        wins_result = await db.execute(
            select(Match).where(
                Match.tournament_id == tournament.id,
                Match.winner_id == player.id,
                Match.status == MatchStatus.finished,
            )
        )
        wins = len(wins_result.scalars().all())
        games_result = await db.execute(
            select(Match).where(
                Match.tournament_id == tournament.id,
                Match.status == MatchStatus.finished,
                (Match.player1_id == player.id) | (Match.player2_id == player.id),
            )
        )
        games = len(games_result.scalars().all())
        losses = games - wins

        entries.append(MobileStandingEntry(
            rank=rank,
            player_id=player.id,
            name=player.name,
            wins=wins,
            losses=losses,
            avg_score=tp.avg_score,
            reg_points=tp.reg_points,
            bonus_points=tp.bonus_points,
            ko_qualified=(rank <= 6),
        ))

    return MobileStandingsResponse(
        tournament_id=tournament.id,
        phase=tournament.status,
        entries=entries,
    )


@router.get("/bracket", response_model=MobileBracketResponse)
async def mobile_bracket(
    _player: Player = Depends(_get_current_player),
    db: AsyncSession = Depends(get_db),
):
    tournament = await _get_active_tournament(db)
    if tournament is None:
        return MobileBracketResponse(tournament_id=None, ko_rounds=[], nebenrunde=[])

    players_result = await db.execute(select(Player))
    player_map: dict[int, str] = {p.id: p.name for p in players_result.scalars().all()}

    ko_result = await db.execute(
        select(Match)
        .where(Match.tournament_id == tournament.id, Match.round_type == RoundType.ko)
        .order_by(Match.id)
    )
    ko_matches = ko_result.scalars().all()

    # Group by position: first 4 = QF, next 2 = SF, next = 3rd place, last = Final
    stages = [
        ("Viertelfinale", ko_matches[:4]),
        ("Halbfinale", ko_matches[4:6]),
        ("Spiel um Platz 3", ko_matches[6:7]),
        ("Finale", ko_matches[7:8]),
    ]
    ko_rounds = []
    for label, stage_matches in stages:
        if not stage_matches:
            continue
        ko_rounds.append(MobileBracketRound(
            label=label,
            matches=[
                MobileBracketMatch(
                    match_id=m.id,
                    player1_name=player_map.get(m.player1_id),
                    player2_name=player_map.get(m.player2_id),
                    winner_name=player_map.get(m.winner_id) if m.winner_id else None,
                    is_completed=(m.status == MatchStatus.finished),
                )
                for m in stage_matches
            ],
        ))

    lightning_result = await db.execute(
        select(Match)
        .where(
            Match.tournament_id == tournament.id,
            Match.round_type == RoundType.lightning,
        )
        .order_by(Match.round_number, Match.id)
    )
    lightning_matches = lightning_result.scalars().all()

    nebenrunde = [
        MobileNebenrundeMatch(
            match_id=m.id,
            round_number=m.round_number,
            player1_name=player_map.get(m.player1_id, "?"),
            player2_name=player_map.get(m.player2_id, "?"),
            winner_name=player_map.get(m.winner_id) if m.winner_id else None,
            is_completed=(m.status == MatchStatus.finished),
        )
        for m in lightning_matches
    ]

    return MobileBracketResponse(
        tournament_id=tournament.id,
        ko_rounds=ko_rounds,
        nebenrunde=nebenrunde,
    )


@router.get("/stats", response_model=MobileStatsResponse)
async def mobile_stats(
    _player: Player = Depends(_get_current_player),
    db: AsyncSession = Depends(get_db),
):
    tournament = await _get_active_tournament(db)
    if tournament is None:
        return MobileStatsResponse(tournament_id=None, players=[], totals={})

    tp_result = await db.execute(
        select(TournamentPlayer, Player)
        .join(Player, TournamentPlayer.player_id == Player.id)
        .where(TournamentPlayer.tournament_id == tournament.id)
    )
    tp_rows = tp_result.all()
    player_map: dict[int, str] = {player.id: player.name for _, player in tp_rows}
    tp_map: dict[int, TournamentPlayer] = {player.id: tp for tp, player in tp_rows}

    events_result = await db.execute(
        select(SpecialEvent)
        .join(Match, SpecialEvent.match_id == Match.id)
        .where(Match.tournament_id == tournament.id)
    )
    all_events = events_result.scalars().all()

    player_events: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    totals: dict[str, int] = defaultdict(int)
    for ev in all_events:
        player_events[ev.player_id][ev.event_type] += 1
        totals[ev.event_type] += 1

    wins_result = await db.execute(
        select(Match.winner_id, Match.id)
        .where(
            Match.tournament_id == tournament.id,
            Match.status == MatchStatus.finished,
        )
    )
    wins_per_player: dict[int, int] = defaultdict(int)
    for winner_id, _ in wins_result.all():
        if winner_id:
            wins_per_player[winner_id] += 1

    games_result = await db.execute(
        select(Match).where(
            Match.tournament_id == tournament.id,
            Match.status == MatchStatus.finished,
        )
    )
    games_per_player: dict[int, int] = defaultdict(int)
    for m in games_result.scalars().all():
        games_per_player[m.player1_id] += 1
        games_per_player[m.player2_id] += 1

    player_stats = [
        MobilePlayerStats(
            player_id=pid,
            name=player_map[pid],
            avg_score=tp_map[pid].avg_score,
            wins=wins_per_player[pid],
            losses=games_per_player[pid] - wins_per_player[pid],
            bonus_points=tp_map[pid].bonus_points,
            event_counts=dict(player_events[pid]),
        )
        for pid in player_map
    ]

    return MobileStatsResponse(
        tournament_id=tournament.id,
        players=sorted(player_stats, key=lambda x: x.avg_score, reverse=True),
        totals=dict(totals),
    )


@router.get("/me", response_model=MobileProfileResponse)
async def mobile_me(
    current_player: Player = Depends(_get_current_player),
    db: AsyncSession = Depends(get_db),
):
    photo_url = (
        f"/static/{current_player.photo_path}" if current_player.photo_path else None
    )

    tournament = await _get_active_tournament(db)
    rank = None
    reg_points = 0.0
    bonus_points = 0
    wins = 0
    losses = 0
    avg_score = 0.0

    if tournament:
        tp_result = await db.execute(
            select(TournamentPlayer, Player)
            .join(Player, TournamentPlayer.player_id == Player.id)
            .where(TournamentPlayer.tournament_id == tournament.id)
            .order_by(TournamentPlayer.reg_points.desc())
        )
        rows = tp_result.all()
        for pos, (tp, player) in enumerate(rows, start=1):
            if player.id == current_player.id:
                rank = pos
                reg_points = tp.reg_points
                bonus_points = tp.bonus_points
                avg_score = tp.avg_score
                break

        wins_result = await db.execute(
            select(Match).where(
                Match.tournament_id == tournament.id,
                Match.winner_id == current_player.id,
                Match.status == MatchStatus.finished,
            )
        )
        wins = len(wins_result.scalars().all())
        games_result = await db.execute(
            select(Match).where(
                Match.tournament_id == tournament.id,
                Match.status == MatchStatus.finished,
                (Match.player1_id == current_player.id)
                | (Match.player2_id == current_player.id),
            )
        )
        losses = len(games_result.scalars().all()) - wins

    return MobileProfileResponse(
        player_id=current_player.id,
        name=current_player.name,
        photo_url=photo_url,
        rank=rank,
        reg_points=reg_points,
        bonus_points=bonus_points,
        wins=wins,
        losses=losses,
        avg_score=avg_score,
    )
