"""Stage 4 — Confluence delivery: generate standardised post-mortem page."""
from __future__ import annotations
from ..models import RCARequest, ConfluenceResult, ConfluenceSection, ActionItem
from .gemini import call_gemini_json


PROMPT = """You are generating a professional Confluence post-mortem page for a production incident.

Incident ID: {incident_id}
Severity: {severity}
CI: {ci}
Opened: {opened_at} | Closed: {closed_at}
Team: {team}
MTTR: {mttr_minutes} minutes
Eureka moment: {eureka_time} — {eureka_description}
Quality score: {quality_score}/100 ({overall_quality})

Work notes:
{work_notes}

Resolution notes:
{resolution_notes}

Generate a complete post-mortem with ALL of these sections:
1. Executive Summary (2-3 sentences, non-technical)
2. Timeline of Events (narrative prose covering key moments)
3. Root Cause Analysis (specific technical root cause, not symptoms)
4. Impact Assessment (who was affected, for how long, estimated scope)
5. Resolution & Recovery (exact steps taken to resolve)
6. Contributing Factors (what conditions allowed this to happen)
7. Action Items (specific, ownable tasks to prevent recurrence)
8. Lessons Learned (what the team should take away)

For action_items, assign realistic owners (use role titles if names unknown).
For tags, include: incident severity, affected service name, root cause category (config/code/infra/dependency/human-error).

Return ONLY valid JSON (no markdown, no backticks):
{{
  "page_title": "string",
  "sections": [
    {{"heading": "string", "content": "string"}}
  ],
  "action_items": [
    {{"owner": "string", "task": "string", "due": "string"}}
  ],
  "tags": ["string"]
}}"""


async def run_confluence(
    req: RCARequest,
    mttr_minutes: int = 0,
    eureka_time: str = "N/A",
    eureka_description: str = "",
    quality_score: int = 0,
    overall_quality: str = "medium",
) -> ConfluenceResult:
    data = await call_gemini_json(
        PROMPT.format(
            incident_id=req.incident_id,
            severity=req.severity,
            ci=req.ci,
            opened_at=req.opened_at,
            closed_at=req.closed_at,
            team=req.team,
            mttr_minutes=mttr_minutes,
            eureka_time=eureka_time,
            eureka_description=eureka_description,
            quality_score=quality_score,
            overall_quality=overall_quality,
            work_notes=req.work_notes,
            resolution_notes=req.resolution_notes,
        ),
        max_tokens=2000,
    )
    sections = [ConfluenceSection(**s) for s in data.get("sections", [])]
    actions = [ActionItem(**a) for a in data.get("action_items", [])]
    return ConfluenceResult(
        page_title=data.get("page_title", f"{req.incident_id} Post-Mortem"),
        sections=sections,
        action_items=actions,
        tags=data.get("tags", []),
    )
