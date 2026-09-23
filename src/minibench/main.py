from fastapi import FastAPI
from sqlalchemy import text

from minibench.db import AsyncSessionLocal
from minibench.settings import settings

app = FastAPI(title="minibench", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict:
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok", "model_mode": settings.model_mode}
