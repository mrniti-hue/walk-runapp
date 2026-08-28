import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_member
from app.core.database import get_db
from app.core.security import create_member_token
from app.models.checkpoint import Checkpoint
from app.models.community import Community
from app.models.team import Team, TeamMember
from app.models.tracking import CheckpointProgress, MemberPosition
from app.schemas.team import (
    LoginRequest,
    LoginResponse,
    MemberCredential,
    PositionSubmitRequest,
    TeamRegisterRequest,
    TeamRegisterResponse,
    TeamStatusResponse,
    TeammatePosition,
)
from app.services.geo import haversine_distance_m
from app.services.passkey import generate_passkey, hash_passkey

router = APIRouter(prefix="/teams", tags=["teams"])

# Suffix letters for member_code, e.g. team "T4821" -> "T4821-A".."T4821-D".
_MEMBER_SUFFIXES = "ABCD"


async def _generate_unique_team_code(db: AsyncSession, community_id) -> str:
    for _ in range(10):
        code = f"T{secrets.randbelow(9000) + 1000}"
        exists = (
            await db.execute(
                select(Team.id).where(Team.community_id == community_id, Team.team_code == code)
            )
        ).scalar_one_or_none()
        if exists is None:
            return code
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "team_code_generation_failed")


@router.post("/register", response_model=TeamRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_team(payload: TeamRegisterRequest, db: AsyncSession = Depends(get_db)):
    community = (
        await db.execute(select(Community).where(Community.slug == payload.community_slug))
    ).scalar_one_or_none()
    if community is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown_community")

    team_code = await _generate_unique_team_code(db, community.id)
    team = Team(community_id=community.id, name=payload.team_name, team_code=team_code)
    db.add(team)
    await db.flush()  # need team.id to attach members

    credentials: list[MemberCredential] = []
    for i, m in enumerate(payload.members):
        passkey = generate_passkey()
        db.add(
            TeamMember(
                team_id=team.id,
                display_name=m.display_name,
                age=m.age,
                email=m.email,
                member_code=_MEMBER_SUFFIXES[i],
                passkey_hash=hash_passkey(passkey),
                is_leader=(i == 0),
            )
        )
        credentials.append(
            MemberCredential(member_code=_MEMBER_SUFFIXES[i], display_name=m.display_name, passkey=passkey)
        )

    await db.commit()
    return TeamRegisterResponse(team_id=str(team.id), team_code=team_code, members=credentials)


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    # passkey_hash is a deterministic hash (sha256+pepper) precisely so login
    # can be a single indexed lookup rather than a scan-and-verify over every
    # member.
    member = (
        await db.execute(select(TeamMember).where(TeamMember.passkey_hash == hash_passkey(payload.passkey)))
    ).scalar_one_or_none()
    if member is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_passkey")

    if member.activated_at is None:
        member.activated_at = datetime.now(timezone.utc)
        await db.commit()

    token = create_member_token(str(member.id), str(member.team_id))
    return LoginResponse(
        access_token=token, member_id=str(member.id), team_id=str(member.team_id), display_name=member.display_name
    )


@router.post("/me/position", status_code=status.HTTP_204_NO_CONTENT)
async def update_my_position(
    payload: PositionSubmitRequest,
    member: TeamMember = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Live location ping for the teammate map — separate from checkpoint claims
    on purpose. A claim means "evaluate me against this checkpoint"; this just
    means "here's where I am right now", sent continuously while walking, so
    it skips the accuracy/radius checks entirely rather than rejecting most of
    a watchPosition stream.
    """
    position = await db.get(MemberPosition, member.id)
    if position is None:
        db.add(
            MemberPosition(
                member_id=member.id,
                team_id=member.team_id,
                lat=payload.lat,
                lng=payload.lng,
                accuracy_m=payload.accuracy_m,
                reported_at=payload.reported_at,
            )
        )
    else:
        position.lat, position.lng, position.accuracy_m = payload.lat, payload.lng, payload.accuracy_m
        position.reported_at = payload.reported_at
    await db.commit()


@router.get("/me/status", response_model=TeamStatusResponse)
async def my_team_status(
    member: TeamMember = Depends(get_current_member), db: AsyncSession = Depends(get_db)
):
    team = await db.get(Team, member.team_id)

    completed = (
        await db.execute(
            select(Checkpoint.slug)
            .join(CheckpointProgress, CheckpointProgress.checkpoint_id == Checkpoint.id)
            .where(CheckpointProgress.team_id == member.team_id)
        )
    ).scalars().all()

    rows = (
        await db.execute(
            select(TeamMember, MemberPosition)
            .outerjoin(MemberPosition, MemberPosition.member_id == TeamMember.id)
            .where(TeamMember.team_id == member.team_id)
        )
    ).all()

    my_position = next((pos for tm, pos in rows if tm.id == member.id and pos is not None), None)

    teammates = []
    for tm, pos in rows:
        distance = None
        if pos is not None and my_position is not None and tm.id != member.id:
            distance = haversine_distance_m(my_position.lat, my_position.lng, pos.lat, pos.lng)
        teammates.append(
            TeammatePosition(
                member_id=str(tm.id),
                display_name=tm.display_name,
                lat=pos.lat if pos else None,
                lng=pos.lng if pos else None,
                updated_at=pos.updated_at if pos else None,
                distance_from_you_m=distance,
            )
        )

    return TeamStatusResponse(
        team_id=str(team.id), team_name=team.name, completed_checkpoints=list(completed), teammates=teammates
    )
