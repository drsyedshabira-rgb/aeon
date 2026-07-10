from pydantic import BaseModel


class CartridgeUploadRequest(BaseModel):
    authority_code: str
    country_code: str
    version: str
    field_mapping: dict
    submission_endpoint: str | None = None
    output_format: str = "xml"


class CartridgeResponse(BaseModel):
    id: str
    authority_code: str
    country_code: str
    version: str
    is_active: bool
    status_note: str | None = None
