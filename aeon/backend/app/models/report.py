import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func, CheckConstraint, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class AdrReport(Base):
    __tablename__ = "adr_reports"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('text','image_ocr','voice','manual_form')", name="ck_reports_source_type"
        ),
        CheckConstraint(
            "status IN ('draft','pending_review','in_flight','submitted','acknowledged','rejected')",
            name="ck_reports_status",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    patient_demographics = Column(JSONB, nullable=False)
    suspect_drugs = Column(JSONB, nullable=False)
    reaction = Column(JSONB, nullable=False)
    narrative = Column(Text, nullable=True)
    source_type = Column(String, nullable=False)
    extraction_confidence = Column(Numeric(3, 2), nullable=True)
    status = Column(String, nullable=False, default="draft")
    target_authority = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
