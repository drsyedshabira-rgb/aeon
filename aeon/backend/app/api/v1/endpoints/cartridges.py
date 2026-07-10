import json
import uuid

import jsonschema
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import require_admin, require_pharmacist
from app.models.base import get_db
from app.models.cartridge import RegulatoryCartridge
from app.schemas.cartridge import CartridgeUploadRequest, CartridgeResponse
from app.cartridges.mapper import CARTRIDGE_DIR

router = APIRouter(prefix="/cartridges", tags=["cartridges"])


@router.post("", response_model=CartridgeResponse)
def upload_cartridge(
    payload: CartridgeUploadRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_admin),
):
    with open(CARTRIDGE_DIR / "cartridge_schema.json") as f:
        meta_schema = json.load(f)

    candidate = payload.dict()
    candidate.setdefault("authority_name", payload.authority_code)
    candidate.setdefault("status", "draft_placeholder")

    try:
        jsonschema.validate(candidate, meta_schema)
    except jsonschema.ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Cartridge failed schema validation: {exc.message}")

    cartridge = RegulatoryCartridge(
        id=uuid.uuid4(),
        authority_code=payload.authority_code,
        country_code=payload.country_code,
        version=payload.version,
        field_mapping=payload.field_mapping,
        submission_endpoint=payload.submission_endpoint,
        is_active=True,
    )
    db.add(cartridge)
    db.commit()
    db.refresh(cartridge)

    return CartridgeResponse(
        id=str(cartridge.id),
        authority_code=cartridge.authority_code,
        country_code=cartridge.country_code,
        version=cartridge.version,
        is_active=cartridge.is_active,
    )


@router.get("", response_model=list[CartridgeResponse])
def list_cartridges(db: Session = Depends(get_db), user: dict = Depends(require_pharmacist)):
    cartridges = db.query(RegulatoryCartridge).filter(RegulatoryCartridge.is_active).all()
    return [
        CartridgeResponse(
            id=str(c.id), authority_code=c.authority_code, country_code=c.country_code,
            version=c.version, is_active=c.is_active,
        )
        for c in cartridges
    ]
