"""
RCA REST API router.
Exposes:
  POST /api/v1/rca              — run full pipeline
  POST /api/v1/rca/stage        — run a single stage
  POST /api/v1/rca/extract      — stage 1 only
  POST /api/v1/rca/timeline     — stage 2 only
  POST /api/v1/rca/quality      — stage 3 only
  POST /api/v1/rca/confluence   — stage 4 only
"""
import asyncio
import logging

from fastapi import APIRouter, HTTPException

from ..models import (
    RCARequest, RCAResponse,
    StageRequest,
    ExtractionResult, TimelineResult, QualityResult, ConfluenceResult,
)
from ..services import (
    run_extraction, run_timeline, run_quality, run_confluence,
)

log = logging.getLogger("rca.router")
router = APIRouter(prefix="/api/v1/rca", tags=["RCA Pipeline"])


# ── Full pipeline ─────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=RCAResponse,
    summary="Run full RCA pipeline",
    description=(
        "Runs all four stages (extraction → timeline → quality → confluence) "
        "and returns the complete structured result. "
        "Stages 3 and 4 receive enriched data from earlier stages."
    ),
)
async def run_full_rca(req: RCARequest) -> RCAResponse:
    log.info("Full RCA pipeline started  incident=%s", req.incident_id)
    errors: dict[str, str] = {}

    # Stage 1 — extraction (required; abort if fails)
    try:
        extraction = await run_extraction(req)
    except Exception as e:
        log.exception("Extraction failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Extraction stage failed: {e}")

    # Stages 2–4 run concurrently — failures are captured but don't abort
    timeline_task = asyncio.create_task(run_timeline(req))
    quality_task  = asyncio.create_task(run_quality(req))

    timeline: TimelineResult | None = None
    quality: QualityResult | None = None

    try:
        timeline = await timeline_task
    except Exception as e:
        log.warning("Timeline stage failed: %s", e)
        errors["timeline"] = str(e)

    try:
        quality = await quality_task
    except Exception as e:
        log.warning("Quality stage failed: %s", e)
        errors["quality"] = str(e)

    # Stage 4 — needs timeline + quality data for richer output
    confluence: ConfluenceResult | None = None
    try:
        confluence = await run_confluence(
            req,
            mttr_minutes=timeline.mttr_minutes if timeline else 0,
            eureka_time=timeline.eureka_moment.time if timeline else "N/A",
            eureka_description=timeline.eureka_moment.description if timeline else "",
            quality_score=quality.quality_score if quality else 0,
            overall_quality=quality.overall_quality if quality else "medium",
        )
    except Exception as e:
        log.warning("Confluence stage failed: %s", e)
        errors["confluence"] = str(e)

    status = "success" if not errors else ("partial" if len(errors) < 3 else "failed")
    log.info("Full RCA pipeline complete  incident=%s  status=%s", req.incident_id, status)

    return RCAResponse(
        incident_id=req.incident_id,
        status=status,
        extraction=extraction,
        timeline=timeline,
        quality=quality,
        confluence=confluence,
        errors=errors,
    )


# ── Individual stage endpoints ────────────────────────────────────────────────

@router.post(
    "/extract",
    response_model=ExtractionResult,
    summary="Stage 1 — Data extraction only",
    description="Extracts structured incident fields and filters automated noise from work notes.",
)
async def extract_only(req: RCARequest) -> ExtractionResult:
    try:
        return await run_extraction(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/timeline",
    response_model=TimelineResult,
    summary="Stage 2 — Timeline & analysis only",
    description="Builds chronological timeline, calculates MTTR, and identifies the Eureka moment.",
)
async def timeline_only(req: RCARequest) -> TimelineResult:
    try:
        return await run_timeline(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/quality",
    response_model=QualityResult,
    summary="Stage 3 — Quality validation only",
    description="Scores the RCA 0–100 and checks CI attachment, resolution depth, and prevention.",
)
async def quality_only(req: RCARequest) -> QualityResult:
    try:
        return await run_quality(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post(
    "/confluence",
    response_model=ConfluenceResult,
    summary="Stage 4 — Confluence page only",
    description="Generates a complete post-mortem page ready for Confluence.",
)
async def confluence_only(req: RCARequest) -> ConfluenceResult:
    try:
        return await run_confluence(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
