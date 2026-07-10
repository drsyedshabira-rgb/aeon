from fastapi import APIRouter

from app.api.v1.endpoints import auth, reports, cartridges, mock_authority

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(reports.router)
api_router.include_router(cartridges.router)
api_router.include_router(mock_authority.router)
