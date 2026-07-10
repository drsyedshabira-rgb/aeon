import base64
import uuid

import jsonschema
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import require_pharmacist, require_admin
from app.models.base import get_db
from app.models.report import AdrReport
from app.models.cartridge import RegulatoryCartridge
from app.models.submission_log import SubmissionLog
from app.models.organization import Organization
from app.nlp.extractor import extractor, ocr_extractor
from app.schemas.report import ReportCreateRequest, ReportCreateResponse, ReportDetailResponse
from app.workers.submission_worker import submit_adr_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportCreateResponse)
def create_report(
    payload: ReportCreateRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_pharmacist),
):
    if not payload.text and not payload.image_base64:
        raise HTTPException(status_code=422, detail="Provide either text or image_base64")

    if payload.image_base64:
        image_bytes = base64.b64decode(payload.image_base64)
        raw_text = ocr_extractor.extract_text_from_image(image_bytes)
        source_type = "image_ocr"
    else:
        raw_text = payload.text
        source_type = "text"

    extracted = extractor.extract(raw_text)

    org = db.query(Organization).filter(Organization.id == user["organization_id"]).first()
    target_authority = _resolve_authority_for_country(db, org.country_code if org else "US")

    report = AdrReport(
        organization_id=user["organization_id"],
        reporter_id=user["user_id"],
        patient_demographics=extracted["patient_demographics"],
        suspect_drugs=extracted["suspect_drugs"],
        reaction=extracted["reaction"],
        narrative=raw_text,
        source_type=source_type,
        extraction_confidence=extracted["confidence"],
        status="pending_review",
        target_authority=target_authority,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return ReportCreateResponse(report_id=str(report.id), status=report.status, extracted=extracted)


@router.get("/{report_id}", response_model=ReportDetailResponse)
def get_report(report_id: str, db: Session = Depends(get_db), user: dict = Depends(require_pharmacist)):
    report = db.query(AdrReport).filter(AdrReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="report not found")

    logs = db.query(SubmissionLog).filter(SubmissionLog.adr_report_id == report.id).all()

    return ReportDetailResponse(
        report_id=str(report.id),
        status=report.status,
        extracted={
            "suspect_drugs": report.suspect_drugs,
            "reaction": report.reaction,
            "patient_demographics": report.patient_demographics,
            "confidence": float(report.extraction_confidence) if report.extraction_confidence else None,
        },
        submission_logs=[
            {"attempt": l.attempt_number, "succeeded": l.succeeded, "status": l.response_status}
            for l in logs
        ],
    )


@router.post("/{report_id}/submit")
def trigger_submission(report_id: str, db: Session = Depends(get_db), user: dict = Depends(require_pharmacist)):
    report = db.query(AdrReport).filter(AdrReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="report not found")

    if report.status in ("submitted", "in_flight"):
        raise HTTPException(
            status_code=422,
            detail=f"Report already {report.status} — cannot resubmit",
        )

    # Set in_flight BEFORE queuing, in the same request, so a second /submit
    # call arriving before the Celery task finishes sees "in_flight" and is
    # rejected — this is what actually closes the race window; checking
    # status alone (previous version) did not, since pending_review covered
    # both "never submitted" and "submission in progress".
    report.status = "in_flight"
    db.commit()

    submit_adr_report.delay(str(report.id))
    return {"status": "queued", "report_id": report_id}


def _resolve_authority_for_country(db: Session, country_code: str) -> str:
    mapping = {"US": "FDA"}  # only FDA is a real, working mapper at this time
    authority = mapping.get(country_code)
    if not authority:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No verified regulatory cartridge available for country '{country_code}' yet. "
                f"Only FDA (US) submission is currently functional; other cartridges are draft "
                f"placeholders pending regulatory verification."
            ),
        )
    return authority
