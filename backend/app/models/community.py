import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Community(Base):
    """
    A community/neighborhood running its own set of routes (e.g. Talat Phlu).
    Every tenant-scoped table links back here via community_id — see
    state-walkruncom.md section 3.1 for why this exists from day one.
    """
    __tablename__ = "communities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # bilingual content: {"th": "...", "en": "..."}
    name_i18n: Mapped[dict] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # --- checkpoint validation policy (event-wide defaults) ---
    # A checkpoint only counts for a team once this many members are inside the
    # radius together — this is what stops a team splitting up to farm
    # checkpoints in parallel. Teams vary 2-4 people, so 2 is the floor.
    quorum_min_members: Mapped[int] = mapped_column(Integer, default=2)
    # How close together (in server-received time) members' arrivals must be
    # to count as "together" — this is what lets the quorum rule tell a team
    # that walked together from one that split up and re-converged by luck.
    quorum_window_seconds: Mapped[int] = mapped_column(Integer, default=300)
    # Urban Bangkok GPS drifts badly between tall buildings; calibrate against
    # the survey in Gps/ before changing.
    default_radius_m: Mapped[int] = mapped_column(Integer, default=40)
    # Fixes coarser than this are rejected outright (usually WiFi-derived).
    max_accuracy_m: Mapped[int] = mapped_column(Integer, default=50)
    # Forces an actual stop at the checkpoint rather than a drive-by.
    default_dwell_seconds: Mapped[int] = mapped_column(Integer, default=45)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
