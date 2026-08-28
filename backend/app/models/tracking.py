import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CheckpointClaim(Base):
    """
    One member's attempt to check in at a checkpoint.

    Every claim is kept, accepted or not — rejected rows are the audit trail
    staff need when a team disputes a result. Positions are validated on the
    server; the client is never trusted to decide it arrived.
    """
    __tablename__ = "checkpoint_claims"
    __table_args__ = (
        # The quorum check reads all claims for one team at one checkpoint.
        Index("ix_claims_checkpoint_team", "checkpoint_id", "team_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("checkpoints.id", ondelete="CASCADE"), index=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("team_members.id", ondelete="CASCADE"), index=True
    )

    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    accuracy_m: Mapped[float] = mapped_column(Float)
    # Server-computed distance from the checkpoint centre. Stored so a disputed
    # claim can be re-read later without recomputing against moved coordinates.
    distance_m: Mapped[float] = mapped_column(Float)

    status: Mapped[str] = mapped_column(String(16))  # accepted | rejected
    # e.g. "too_far" | "low_accuracy" | "dwell_too_short" | "impossible_speed"
    reject_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Device clock — untrusted, kept only to spot clock tampering.
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CheckpointProgress(Base):
    """
    A checkpoint the team has actually completed — written once the quorum of
    members has been inside the radius together. This is the scoring record;
    individual accepted claims on their own do not count.
    """
    __tablename__ = "checkpoint_progress"
    __table_args__ = (
        UniqueConstraint("team_id", "checkpoint_id", name="uq_progress_team_checkpoint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), index=True
    )
    checkpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("checkpoints.id", ondelete="CASCADE"), index=True
    )
    # How many members were present when it completed — kept for staff review.
    member_count: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MemberPosition(Base):
    """
    Latest known position of one member, updated in place.

    Feeds the teammate map and the "you are 350m from your team" warning. Only
    the current fix is kept rather than a full track: comparing an incoming fix
    against the stored one is enough to catch impossible speeds, and it keeps
    this table at one row per participant.
    """
    __tablename__ = "member_positions"

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("team_members.id", ondelete="CASCADE"), primary_key=True
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), index=True
    )

    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    accuracy_m: Mapped[float] = mapped_column(Float)

    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
