from fastapi import APIRouter, Request

router = APIRouter(prefix="/_mock_authority", tags=["mock_authority"])


@router.post("/fda")
async def mock_fda_endpoint(request: Request):
    """Simple mock authority endpoint that accepts XML payloads and
    returns a 200 OK to simulate successful submission.
    """
    # Read payload for logging/debugging (don't store in prod)
    body = await request.body()
    # For now, always accept and return a simple acknowledgment
    return {"received_bytes": len(body), "status": "accepted"}
