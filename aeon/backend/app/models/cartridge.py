import uuid
from sqlalchemy import Column, String, Boolean, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class RegulatoryCartridge(Base):
    __tablename__ = "regulatory_cartridges"
    __table_args__ = (
        UniqueConstraint("authority_code", "version", name="uq_authority_version"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    authority_code = Column(String, nullable=False)
    country_code = Column(String(2), nullable=False)
    version = Column(String, nullable=False)
    field_mapping = Column(JSONB, nullable=False)
    submission_endpoint = Column(String, nullable=True)
    auth_config = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
