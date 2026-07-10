import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class SubmissionLog(Base):
    __tablename__ = "submission_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    adr_report_id = Column(UUID(as_uuid=True), ForeignKey("adr_reports.id"))
    cartridge_id = Column(UUID(as_uuid=True), ForeignKey("regulatory_cartridges.id"))
    attempt_number = Column(Integer, nullable=False, default=1)
    request_payload = Column(JSONB, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    succeeded = Column(Boolean, nullable=True)
    attempted_at = Column(DateTime(timezone=True), server_default=func.now())
