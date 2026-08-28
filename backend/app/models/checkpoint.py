import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Checkpoint(Base):
    """
    A stop on the route — a historical site with bilingual content to read.

    Coordinates are plain lat/lng and distance is computed with haversine in the
    service layer. PostGIS would be the textbook answer but it is not in the
    postgres:16-alpine image, and with a handful of checkpoints and ~200 users
    the extra dependency buys nothing.
    """
    __tablename__ = "checkpoints"
    __table_args__ = (
        UniqueConstraint("community_id", "slug", name="uq_checkpoints_community_slug"),
        UniqueConstraint("community_id", "sequence", name="uq_checkpoints_community_sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), index=True
    )
    # Visiting order along the route, 1-based.
    sequence: Mapped[int] = mapped_column(Integer)
    slug: Mapped[str] = mapped_column(String(64))
    # bilingual content: {"th": "...", "en": "..."}
    name_i18n: Mapped[dict] = mapped_column(JSONB)
    content_i18n: Mapped[dict] = mapped_column(JSONB, default=dict)

    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)

    # Both fall back to the community defaults when NULL. Override per checkpoint
    # where the survey shows bad reception (narrow sois, under the BTS).
    radius_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dwell_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
