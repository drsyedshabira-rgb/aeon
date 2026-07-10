from fastapi import FastAPI

from app.api.v1.router import api_router
from app.models.base import Base, engine

app = FastAPI(title="AEON — Adverse Event Orchestration Nexus")
app.include_router(api_router)


@app.on_event("startup")
def on_startup():
    # In production, use `alembic upgrade head` instead of create_all.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}
