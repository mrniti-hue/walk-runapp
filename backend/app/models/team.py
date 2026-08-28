import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Team(Base):
    """
    A registered group walking the route together (2-4 people).
    Teams are the unit that scores — see CheckpointProgress for why individual
    arrivals alone don't complete a checkpoint.
    """
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("community_id", "team_code", name="uq_teams_community_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    # Short human-readable code read aloud at the start line, e.g. "TPL-4821".
    team_code: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(16), default="registered")  # registered | started | finished
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list["TeamMember"]] = relationship(back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    """
    One person on a team. Each member gets their OWN passkey rather than the team
    sharing one — without per-member identity the server cannot tell whose device
    is reporting a position, so off-route detection and the checkpoint quorum
    would both be impossible.
    """
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "member_code", name="uq_team_members_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), index=True
    )
    display_name: Mapped[str] = mapped_column(String(120))
    age: Mapped[int] = mapped_column(Integer)
    # Optional — only used to deliver the passkey. Never verified, so it must not
    # be treated as an identity.
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Suffix of the team code shown in the UI and to support staff, e.g. "A" in
    # "TPL-4821-A". Public — it is NOT the secret.
    member_code: Mapped[str] = mapped_column(String(8))
    # sha256(pepper + passkey). Deterministic on purpose: login is a single
    # indexed lookup by hash. bcrypt would be unsearchable here, and the passkey
    # is high-entropy random rather than a user-chosen password.
    passkey_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    is_leader: Mapped[bool] = mapped_column(Boolean, default=False)
    # First time this passkey was actually used — lets staff see who never showed.
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team: Mapped["Team"] = relationship(back_populates="members")
