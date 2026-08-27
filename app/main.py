"""
app/main.py

FastAPI app entry point. Run locally with:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import routes, webhook
from app.database.database import init_db
from app.utils.logging import get_logger

log = get_logger("APP")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting up -- initializing database")
    await init_db()
    log.info("Startup complete")
    yield
    log.info("Shutting down")


app = FastAPI(title="Instagram AI Agent", lifespan=lifespan)

app.include_router(routes.router)
app.include_router(webhook.router)
