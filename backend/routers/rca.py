"""
RCA REST API router.

Endpoints:
  POST /api/v1/rca                       manual text → full pipeline
  POST /api/v1/rca/from-servicenow       incident number → ServiceNow fetch → pipeline → Confluence publish
  GET  /api/v1/rca/servicenow/{number}   fetch raw incident from ServiceNow (no pipeline)
  POST /api/v1/rca/extract               stage 1 only
  POST /api/v1/rca/timeline              stage 2 only
  POST /api/v1/rca/quality               stage 3 only
  POST /api/v1/rca/confluence            stage 4 — generate content only (no publish)
"""
import asyncio
import logging

from fastapi import APIRouter, HTTPException, Path

from ..models import (
    RCARequest, SNRCARequest, RCAResponse,
    ConfluencePublishResult, SNFetchResult,
    ExtractionResult, TimelineResult, QualityResult, ConfluenceResult,
)
from ..services import (
    run_extraction, run_timeline, run_quality, run_confluence,
    fetch_incident, format_audit_for_llm,
    create_postmortem_page, page_exists,
)

log = logging.getLogger("rca.router")
router = APIRouter(prefix="/api/v1/rca", tags=["RCA Pipeline"])


# ── Core pipeline (reused by both endpoints) ──────────────────────

async def _run_pipeline(req: RCARequest, publish: bool = False) -> RCAResponse:
    errors: dict[str, str] = {}

    # Stage 1 — required
    try:
        extraction = await run_extraction(req)
    except Exception as e:
        log.exception("Extraction failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Extraction stage failed: {e}")

    # Stages 2 + 3 — concurrent
    tl_task = asyncio.create_task(run_timeline(req))
    q_task  = asyncio.create_task(run_quality(req))

    timeline: TimelineResult | None = None
    quality:  QualityResult  | None = None

    try:
        timeline = await tl_task
    except Exception as e:
        log.warning("Timeline failed: %s", e)
        errors["timeline"] = str(e)

    try:
        quality = await q_task
    except Exception as e:
        log.warning("Quality failed: %s", e)
        errors["quality"] = str(e)

    # Stage 4 — generate Confluence content
    confluence: ConfluenceResult | None = None
    try:
        confluence = await run_confluence(
            req,
            mttr_minutes       = timeline.mttr_minutes             if timeline else 0,
            eureka_time        = timeline.eureka_moment.time        if timeline else "N/A",
            eureka_description = timeline.eureka_moment.description if timeline else "",
            quality_score      = quality.quality_score              if quality  else 0,
            overall_quality    = quality.overall_quality            if quality  else "medium",
        )
    except Exception as e:
        log.warning("Confluence generate failed: %s", e)
        errors["confluence"] = str(e)

    # Stage 5 (optional) — publish to Confluence
    published: ConfluencePublishResult | None = None
    if publish and confluence:
        try:
            if await page_exists(confluence.page_title):
                errors["confluence_publish"] = f"Page '{confluence.page_title}' already exists — skipped."
            else:
                raw = await create_postmortem_page(
                    result          = confluence,
                    incident_id     = req.incident_id,
                    severity        = req.severity,
                    ci              = req.ci,
                    mttr_minutes    = timeline.mttr_minutes    if timeline else 0,
                    quality_score   = quality.quality_score    if quality  else 0,
                    overall_quality = quality.overall_quality  if quality  else "medium",
                    opened_at       = req.opened_at,
                    closed_at       = req.closed_at,
                    team            = req.team,
                )
                published = ConfluencePublishResult(**raw)
        except Exception as e:
            log.warning("Confluence publish failed: %s", e)
            errors["confluence_publish"] = str(e)

    status = "success" if not errors else ("partial" if len(errors) < 3 else "failed")

    return RCAResponse(
        incident_id               = req.incident_id,
        status                    = status,
        extraction                = extraction,
        timeline                  = timeline,
        quality                   = quality,
        confluence                = confluence,
        confluence_page_published = published,
        errors                    = errors,
    )


# ── POST /api/v1/rca — manual text input ─────────────────────────

@router.post(
    "",
    response_model=RCAResponse,
    summary="Full pipeline — manual text input",
    description="Paste incident text directly. Runs all 4 stages. Does not auto-publish to Confluence.",
)
async def run_full_rca(req: RCARequest) -> RCAResponse:
    log.info("Manual RCA pipeline  incident=%s", req.incident_id)
    result = await _run_pipeline(req, publish=False)
    log.info("Manual RCA complete  incident=%s  status=%s", req.incident_id, result.status)
    return result


# ── POST /api/v1/rca/from-servicenow — full end-to-end ───────────

@router.post(
    "/from-servicenow",
    response_model=RCAResponse,
    summary="Full end-to-end: ServiceNow → Gemini → Confluence",
    description=(
        "Supply just an incident number. The backend fetches all incident data, "
        "audit logs, and work notes from ServiceNow, runs the full AI pipeline, "
        "and automatically publishes the post-mortem to Confluence."
    ),
)
async def run_from_servicenow(req: SNRCARequest) -> RCAResponse:
    log.info("ServiceNow RCA pipeline  incident=%s", req.incident_number)

    try:
        incident = await fetch_incident(req.incident_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("ServiceNow fetch failed: %s", e)
        raise HTTPException(status_code=502, detail=f"ServiceNow fetch failed: {e}")

    combined_notes = await format_audit_for_llm(incident)

    rca_req = RCARequest(
        incident_id      = incident.incident_id,
        severity         = incident.severity,
        ci               = incident.ci,
        opened_at        = incident.opened_at,
        closed_at        = incident.closed_at,
        team             = incident.team,
        work_notes       = combined_notes,
        resolution_notes = incident.resolution or incident.description or "No resolution notes available.",
    )

    result = await _run_pipeline(rca_req, publish=req.publish_to_confluence)

    result.servicenow_fetch = SNFetchResult(
        incident_id    = incident.incident_id,
        sys_id         = incident.sys_id,
        severity       = incident.severity,
        ci             = incident.ci,
        opened_at      = incident.opened_at,
        closed_at      = incident.closed_at,
        team           = incident.team,
        short_desc     = incident.short_desc,
        work_notes_raw = incident.work_notes_raw,
        audit_count    = len(incident.audit_entries),
    )

    log.info(
        "ServiceNow RCA complete  incident=%s  status=%s  published=%s",
        req.incident_number, result.status, bool(result.confluence_page_published),
    )
    return result


# ── GET /api/v1/rca/servicenow/{number} — fetch only ─────────────

@router.get(
    "/servicenow/{incident_number}",
    response_model=SNFetchResult,
    summary="Fetch raw incident from ServiceNow — no pipeline",
    description="Fetches incident + work notes + audit log from ServiceNow. Use this to verify your ServiceNow connection before running the full pipeline.",
)
async def fetch_sn_incident(
    incident_number: str = Path(..., examples=["INC0091847"]),
) -> SNFetchResult:
    try:
        incident = await fetch_incident(incident_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("ServiceNow fetch failed: %s", e)
        raise HTTPException(status_code=502, detail=f"ServiceNow fetch failed: {e}")

    return SNFetchResult(
        incident_id    = incident.incident_id,
        sys_id         = incident.sys_id,
        severity       = incident.severity,
        ci             = incident.ci,
        opened_at      = incident.opened_at,
        closed_at      = incident.closed_at,
        team           = incident.team,
        short_desc     = incident.short_desc,
        work_notes_raw = incident.work_notes_raw,
        audit_count    = len(incident.audit_entries),
    )


# ── Individual stage endpoints ────────────────────────────────────

@router.post("/extract",    response_model=ExtractionResult, summary="Stage 1 — extraction only")
async def extract_only(req: RCARequest) -> ExtractionResult:
    try:
        return await run_extraction(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/timeline",   response_model=TimelineResult,   summary="Stage 2 — timeline only")
async def timeline_only(req: RCARequest) -> TimelineResult:
    try:
        return await run_timeline(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/quality",    response_model=QualityResult,    summary="Stage 3 — quality only")
async def quality_only(req: RCARequest) -> QualityResult:
    try:
        return await run_quality(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/confluence",  response_model=ConfluenceResult, summary="Stage 4 — generate content only (no publish)")
async def confluence_only(req: RCARequest) -> ConfluenceResult:
    try:
        return await run_confluence(req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
