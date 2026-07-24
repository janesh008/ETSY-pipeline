"""CraftDesk API — FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from craftdesk_api.core.config import settings
from craftdesk_api.routers import auth, etsy, gcp, pipeline, prompts, review

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-powered Etsy automation and digital asset management SaaS platform.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1")
app.include_router(gcp.router, prefix="/api/v1")
app.include_router(prompts.router, prefix="/api/v1")
app.include_router(etsy.router, prefix="/api/v1")
app.include_router(pipeline.router, prefix="/api/v1")
app.include_router(review.router, prefix="/api/v1")


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"], summary="Health check")
async def health() -> dict[str, str]:
    """Return service health status. Used by load balancers and monitoring."""
    return {"status": "ok", "service": settings.app_name}
