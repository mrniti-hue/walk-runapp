import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_member
from app.core.database import get_db
from app.models.checkpoint import Checkpoint
from app.models.community import Community
from app.models.team import Team, TeamMember
from app.models.tracking import CheckpointClaim, CheckpointProgress, MemberPosition
from app.schemas.team import PositionSubmitRequest, PositionSubmitResponse
from app.services.checkpoint_rules import evaluate_position, find_quorum_completion, first_dwell_satisfied_at

router = APIRouter(prefix="/checkpoints", tags=["checkpoints"])


@router.get("")
async def list_checkpoints(community_slug: str, db: AsyncSession = Depends(get_db)):
    community = (
        await db.execute(select(Community).where(Community.slug == community_slug))
    ).scalar_one_or_none()
    if community is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown_community")

    checkpoints = (
        await db.execute(
            select(Checkpoint)
            .where(Checkpoint.community_id == community.id, Checkpoint.is_active.is_(True))
            .order_by(Checkpoint.sequence)
        )
    ).scalars().all()

    return [
        {
            "id": str(c.id),
            "sequence": c.sequence,
            "slug": c.slug,
            "name_i18n": c.name_i18n,
            "lat": c.lat,
            "lng": c.lng,
        }
        for c in checkpoints
    ]


@router.post("/{checkpoint_id}/claim", response_model=PositionSubmitResponse)
async def claim_checkpoint(
    checkpoint_id: uuid.UUID,
    payload: PositionSubmitRequest,
    member: TeamMember = Depends(get_current_member),
    db: AsyncSession = Depends(get_db),
):
    checkpoint = await db.get(Checkpoint, checkpoint_id)
    team = await db.get(Team, member.team_id)
    if checkpoint is None or not checkpoint.is_active or checkpoint.community_id != team.community_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown_checkpoint")

    community = await db.get(Community, checkpoint.community_id)

    result = evaluate_position(
        checkpoint_lat=checkpoint.lat,
        checkpoint_lng=checkpoint.lng,
        radius_m=checkpoint.radius_m or community.default_radius_m,
        max_accuracy_m=community.max_accuracy_m,
        lat=payload.lat,
        lng=payload.lng,
        accuracy_m=payload.accuracy_m,
    )

    # Server-received time, not the client-reported clock, is what drives
    # dwell/quorum below — reported_at is stored purely for audit, since a
    # client could otherwise fake a long dwell by lying about its own clock.
    received_at = datetime.now(timezone.utc)

    db.add(
        CheckpointClaim(
            checkpoint_id=checkpoint.id,
            team_id=member.team_id,
            member_id=member.id,
            lat=payload.lat,
            lng=payload.lng,
            accuracy_m=payload.accuracy_m,
            distance_m=result.distance_m,
            status="accepted" if result.accepted else "rejected",
            reject_reason=result.reject_reason,
            reported_at=payload.reported_at,
            received_at=received_at,
        )
    )

    if result.accepted:
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

    checkpoint_completed = False

    already_done = (
        await db.execute(
            select(CheckpointProgress.id).where(
                CheckpointProgress.team_id == member.team_id,
                CheckpointProgress.checkpoint_id == checkpoint.id,
            )
        )
    ).scalar_one_or_none()

    if result.accepted and already_done is None:
        # Re-derive completion from the whole claim history rather than just
        # this submission — the quorum may only complete once we account for
        # everyone else's earlier accepted claims too.
        past_claims = (
            await db.execute(
                select(CheckpointClaim.member_id, CheckpointClaim.received_at).where(
                    CheckpointClaim.checkpoint_id == checkpoint.id,
                    CheckpointClaim.team_id == member.team_id,
                    CheckpointClaim.status == "accepted",
                )
            )
        ).all()

        by_member: dict[uuid.UUID, list[datetime]] = {}
        for member_id, claim_received_at in past_claims:
            by_member.setdefault(member_id, []).append(claim_received_at)
        by_member.setdefault(member.id, []).append(received_at)

        dwell_required = checkpoint.dwell_seconds or community.default_dwell_seconds
        arrivals = {
            mid: arrival
            for mid, times in by_member.items()
            if (arrival := first_dwell_satisfied_at(times, required_seconds=dwell_required)) is not None
        }

        quorum = find_quorum_completion(
            arrivals,
            min_members=community.quorum_min_members,
            quorum_window_seconds=community.quorum_window_seconds,
        )
        if quorum is not None:
            completed_at, counted_members = quorum
            db.add(
                CheckpointProgress(
                    team_id=member.team_id,
                    checkpoint_id=checkpoint.id,
                    member_count=len(counted_members),
                    completed_at=completed_at,
                )
            )
            checkpoint_completed = True

    await db.commit()

    return PositionSubmitResponse(
        accepted=result.accepted,
        reject_reason=result.reject_reason,
        distance_m=result.distance_m,
        checkpoint_completed=checkpoint_completed,
    )
