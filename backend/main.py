"""
RCA Agent — FastAPI backend
- Exposes a full REST API (usable standalone by any consumer)
- Vertex AI / Gemini via Application Default Credentials (GCP ADC)
- CORS configured for the separate frontend service
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import rca_router
from .services import init_gemini

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger("rca.main")

# ── Config ───────────────────────────────────────────────────────────────────
GCP_PROJECT_ID  = os.environ.get("GCP_PROJECT_ID")
GCP_LOCATION    = os.environ.get("GCP_LOCATION", "us-central1")
GEMINI_MODEL    = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
PORT            = int(os.environ.get("PORT", 8080))

# Comma-separated allowed origins for CORS.
# Default allows localhost dev + any *.run.app (Cloud Run) origin.
CORS_ORIGINS_RAW = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://localhost:80"
)
CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS_RAW.split(",") if o.strip()]


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not GCP_PROJECT_ID:
        raise RuntimeError(
            "GCP_PROJECT_ID is not set.\n"
            "Run: export GCP_PROJECT_ID=your-project  or  -e GCP_PROJECT_ID=... in Docker"
        )
    init_gemini(GCP_PROJECT_ID, GCP_LOCATION, GEMINI_MODEL)
    log.info(
        "RCA Agent ready  project=%s  location=%s  model=%s  port=%s",
        GCP_PROJECT_ID, GCP_LOCATION, GEMINI_MODEL, PORT,
    )
    yield
    log.info("RCA Agent shutting down")


# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="RCA Agent API",
    description=(
        "AI-powered Root Cause Analysis pipeline.\n\n"
        "Pulls incident data from ServiceNow, builds a timeline, validates quality, "
        "and generates a Confluence post-mortem — powered by Vertex AI / Gemini.\n\n"
        "Can be consumed directly via REST API or via the RCA Agent UI."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS — allow the separate frontend service and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.run\.app",   # any Cloud Run service
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(rca_router)


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "ok",
        "project": GCP_PROJECT_ID,
        "location": GCP_LOCATION,
        "model": GEMINI_MODEL,
    }


# ── Dev entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=PORT, reload=True)
