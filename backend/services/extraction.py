"""Stage 1 — Data extraction: pull structured fields, filter automated noise."""
from __future__ import annotations
from models import RCARequest, ExtractionResult, HumanNote
from .gemini import call_gemini_json


PROMPT = """You are an RCA data extraction agent processing a ServiceNow incident export.

Incident ID: {incident_id}
Severity: {severity}
CI: {ci}
Opened: {opened_at}
Closed: {closed_at}
Team: {team}

Work notes (raw export):
{work_notes}

Resolution notes:
{resolution_notes}

Instructions:
- Extract all structured fields
- For human_notes, include ONLY entries written by a human engineer. Filter out any line containing words like: AUTOMATED, automated, health check retry, monitoring system, alert resolved, system triggered, auto-resolved, policy triggered
- Set ci_attached to true if a CMDB CI reference (e.g. CI-XXXXX) appears in the CI field
- key_actors: real names of people mentioned (not system names)
- affected_components: service/system names mentioned

Return ONLY a valid JSON object (no markdown, no backticks, no preamble) with this exact structure:
{{
  "incident_id": "string",
  "severity": "string",
  "ci_name": "string",
  "ci_attached": true,
  "opened_at": "string",
  "closed_at": "string",
  "team": "string",
  "human_notes": [
    {{"time": "string", "author_type": "human", "note": "string"}}
  ],
  "automated_entries_filtered": 0,
  "key_actors": ["string"],
  "affected_components": ["string"]
}}"""


async def run_extraction(req: RCARequest) -> ExtractionResult:
    data = await call_gemini_json(
        PROMPT.format(
            incident_id      = req.incident_id,
            severity         = req.severity,
            ci               = req.ci,
            opened_at        = req.opened_at,
            closed_at        = req.closed_at,
            team             = req.team,
            work_notes       = (req.work_notes or "")[:8000],  # cap to avoid prompt overflow
            resolution_notes = req.resolution_notes,
        )
    )
    notes = [HumanNote(**n) for n in data.get("human_notes", [])]
    return ExtractionResult(
        incident_id                = data.get("incident_id", req.incident_id),
        severity                   = data.get("severity", req.severity),
        ci_name                    = data.get("ci_name", req.ci),
        ci_attached                = bool(data.get("ci_attached", False)),
        opened_at                  = data.get("opened_at", req.opened_at),
        closed_at                  = data.get("closed_at", req.closed_at),
        team                       = data.get("team", req.team),
        human_notes                = notes,
        automated_entries_filtered = int(data.get("automated_entries_filtered", 0)),
        key_actors                 = data.get("key_actors", []),
        affected_components        = data.get("affected_components", []),
    )
