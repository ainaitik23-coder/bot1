"""
app/api/routes.py

Non-webhook routes -- health checks, debug endpoints.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    return {"status": "ok", "service": "instagram-ai-agent"}


@router.get("/health")
async def health():
    return {"status": "healthy"}
