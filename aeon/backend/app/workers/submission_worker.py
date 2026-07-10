"""
app/workers/submission_worker.py
Real Celery task replacing the MVP's asyncio.create_task simulation.
Uses tenacity for exponential-backoff retry (5 attempts).
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.celery_app import celery_app
from app.models.base import SessionLocal
from app.models.report import AdrReport
from app.models.cartridge import RegulatoryCartridge
from app.models.submission_log import SubmissionLog
from app.cartridges.mapper import map_report


class TransientSubmissionError(Exception):
    pass


class PermanentSubmissionError(Exception):
    pass


@retry(
    retry=retry_if_exception_type(TransientSubmissionError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    reraise=True,
)
def _call_authority_api(endpoint: str, payload: str, auth_config: dict) -> httpx.Response:
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(endpoint, content=payload, headers={"Content-Type": "application/xml"})
    except httpx.RequestError as exc:
        # DNS failure, connection refused, timeout, etc. — treat as transient so
        # tenacity retries it, same as a 5xx. A placeholder/unreachable endpoint
        # (like the FDA cartridge's example.com default) will hit this path.
        raise TransientSubmissionError(f"request failed: {exc!r}") from exc

    if response.status_code >= 500:
        raise TransientSubmissionError(f"{response.status_code}: {response.text}")
    if response.status_code >= 400:
        raise PermanentSubmissionError(f"{response.status_code}: {response.text}")

    return response


@celery_app.task(bind=True, max_retries=5)
def submit_adr_report(self, report_id: str):
    db = SessionLocal()
    try:
        report = db.query(AdrReport).filter(AdrReport.id == report_id).first()
        if not report:
            return {"error": "report not found"}

        cartridge = (
            db.query(RegulatoryCartridge)
            .filter(RegulatoryCartridge.authority_code == report.target_authority, RegulatoryCartridge.is_active)
            .order_by(RegulatoryCartridge.created_at.desc())
            .first()
        )
        if not cartridge:
            report.status = "rejected"
            db.commit()
            return {"error": f"no active cartridge for {report.target_authority}"}

        mapped = map_report(
            authority_code=report.target_authority,
            report_id=str(report.id),
            pharmacy_id=str(report.organization_id),
            extracted={
                "suspect_drugs": report.suspect_drugs,
                "reaction": report.reaction,
                "patient_demographics": report.patient_demographics,
            },
            narrative=report.narrative or "",
        )

        attempt_number = self.request.retries + 1
        succeeded = False
        response_status = None
        response_body = None

        try:
            response = _call_authority_api(
                cartridge.submission_endpoint, mapped["payload"], cartridge.auth_config or {}
            )
            succeeded = True
            response_status = response.status_code
            response_body = response.text
            report.status = "submitted"

        except PermanentSubmissionError as exc:
            succeeded = False
            response_body = str(exc)
            report.status = "rejected"

        except TransientSubmissionError as exc:
            # tenacity already exhausted its retries inside _call_authority_api;
            # this is the final failure after 5 attempts
            succeeded = False
            response_body = str(exc)
            report.status = "rejected"

        db.add(SubmissionLog(
            adr_report_id=report.id,
            cartridge_id=cartridge.id,
            attempt_number=attempt_number,
            request_payload={"payload": mapped["payload"][:2000]},  # truncate for storage
            response_status=response_status,
            response_body=response_body,
            succeeded=succeeded,
        ))
        db.commit()

        return {"report_id": str(report.id), "succeeded": succeeded}

    finally:
        db.close()
