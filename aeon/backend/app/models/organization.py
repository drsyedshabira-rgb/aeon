import uuid
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    country_code = Column(String(2), nullable=False)
    plan = Column(String, nullable=False, default="starter")
    stripe_customer_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
