"""
RCA Agent — FastAPI backend
Initialises: Vertex AI / Gemini, ServiceNow client, Confluence client.
All credentials come from environment variables — no secrets in code.
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import rca_router
from services import init_gemini, init_servicenow, init_confluence

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger("rca.main")

# ── Config ────────────────────────────────────────────────────────
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_LOCATION   = os.environ.get("GCP_LOCATION", "us-central1")
GEMINI_MODEL   = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
PORT           = int(os.environ.get("PORT", 8080))

SN_INSTANCE = os.environ.get("SERVICENOW_INSTANCE", "")
SN_USERNAME = os.environ.get("SERVICENOW_USERNAME", "")
SN_PASSWORD = os.environ.get("SERVICENOW_PASSWORD", "")

CONF_BASE_URL       = os.environ.get("CONFLUENCE_BASE_URL", "")
CONF_USERNAME       = os.environ.get("CONFLUENCE_USERNAME", "")
CONF_API_TOKEN      = os.environ.get("CONFLUENCE_API_TOKEN", "")
CONF_SPACE_KEY      = os.environ.get("CONFLUENCE_SPACE_KEY", "")
CONF_PARENT_PAGE_ID = os.environ.get("CONFLUENCE_PARENT_PAGE_ID", "")

CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:8501,http://localhost:3000").split(",")
    if o.strip()
]


# ── Lifespan ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not GCP_PROJECT_ID:
        raise RuntimeError(
            "GCP_PROJECT_ID is not set.\n"
            "Add it to backend.env:  GCP_PROJECT_ID=your-project-id"
        )
    init_gemini(GCP_PROJECT_ID, GCP_LOCATION, GEMINI_MODEL)

    if SN_INSTANCE and SN_USERNAME and SN_PASSWORD:
        init_servicenow(SN_INSTANCE, SN_USERNAME, SN_PASSWORD)
    else:
        log.warning(
            "ServiceNow credentials not set — "
            "/api/v1/rca/from-servicenow will fail. "
            "Set SERVICENOW_INSTANCE, SERVICENOW_USERNAME, SERVICENOW_PASSWORD."
        )

    if CONF_BASE_URL and CONF_USERNAME and CONF_API_TOKEN and CONF_SPACE_KEY:
        init_confluence(
            CONF_BASE_URL, CONF_USERNAME, CONF_API_TOKEN,
            CONF_SPACE_KEY, CONF_PARENT_PAGE_ID,
        )
    else:
        log.warning(
            "Confluence credentials not set — publish_to_confluence=true will fail. "
            "Set CONFLUENCE_BASE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN, CONFLUENCE_SPACE_KEY."
        )

    log.info(
        "RCA Agent ready  project=%s  location=%s  model=%s  port=%s  "
        "servicenow=%s  confluence=%s",
        GCP_PROJECT_ID, GCP_LOCATION, GEMINI_MODEL, PORT,
        bool(SN_INSTANCE), bool(CONF_BASE_URL),
    )
    yield
    log.info("RCA Agent shutting down")


# ── App ───────────────────────────────────────────────────────────
app = FastAPI(
    title="RCA Agent API",
    description=(
        "AI-powered Root Cause Analysis pipeline.\n\n"
        "**End-to-end:** `POST /api/v1/rca/from-servicenow` — incident number in, "
        "Confluence page out.\n\n"
        "**Manual:** `POST /api/v1/rca` — paste incident text directly.\n\n"
        "**Debug:** `GET /api/v1/rca/servicenow/{number}` — test ServiceNow connectivity."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.run\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rca_router)


@app.get("/health", tags=["System"], summary="Health check")
async def health():
    return {
        "status":                  "ok",
        "project":                 GCP_PROJECT_ID,
        "location":                GCP_LOCATION,
        "model":                   GEMINI_MODEL,
        "servicenow_configured":   bool(SN_INSTANCE and SN_USERNAME),
        "confluence_configured":   bool(CONF_BASE_URL and CONF_API_TOKEN),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
