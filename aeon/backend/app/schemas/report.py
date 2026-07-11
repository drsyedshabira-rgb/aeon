from typing import Optional
from pydantic import BaseModel


class ReportCreateRequest(BaseModel):
    text: Optional[str] = None
    image_base64: Optional[str] = None
    pharmacy_id: Optional[str] = None
    country: Optional[str] = None


class ReportCreateResponse(BaseModel):
    report_id: str
    status: str
    extracted: dict


class ReportDetailResponse(BaseModel):
    report_id: str
    status: str
    extracted: dict
    xml_payload: Optional[str] = None
    submission_logs: list = []
