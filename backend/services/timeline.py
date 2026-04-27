"""Stage 2 — Timeline & analysis: MTTR, Eureka moment, chronological narrative."""
from __future__ import annotations
from models import RCARequest, TimelineResult, TimelineEvent, EurekaEvent
from gemini import call_gemini_json


PROMPT = """You are an RCA timeline analyst. Build a precise chronological analysis of this incident.

Incident: {incident_id} | {severity} | {ci}
Opened: {opened_at} | Closed: {closed_at}
Team: {team}

Work notes:
{work_notes}

Resolution notes:
{resolution_notes}

Instructions:
- Calculate mttr_minutes as the total minutes from opened_at to closed_at
- time_to_detect_minutes: from first symptom/alert to when on-call was engaged
- time_to_diagnose_minutes: from alert to when root cause was positively identified
- time_to_fix_minutes: from root cause identified to fix applied and confirmed working
- eureka_moment: the EXACT moment root cause was identified — be specific
- timeline: all significant events in order. Each event must have a category:
    detection = first signs / alerts
    investigation = exploring possible causes
    diagnosis = root cause confirmed
    fix = remediation applied
    recovery = service restored and validated
- Mark is_eureka: true on the single event where root cause was confirmed
- narrative_summary: 2-3 sentences plain-English story of what happened

Return ONLY valid JSON (no markdown, no backticks):
{{
  "mttr_minutes": 0,
  "time_to_detect_minutes": 0,
  "time_to_diagnose_minutes": 0,
  "time_to_fix_minutes": 0,
  "eureka_moment": {{"time": "string", "description": "string"}},
  "timeline": [
    {{"time": "string", "event": "string", "category": "detection|investigation|diagnosis|fix|recovery", "is_eureka": false}}
  ],
  "narrative_summary": "string"
}}"""


async def run_timeline(req: RCARequest) -> TimelineResult:
    data = await call_gemini_json(
        PROMPT.format(
            incident_id      = req.incident_id,
            severity         = req.severity,
            ci               = req.ci,
            opened_at        = req.opened_at,
            closed_at        = req.closed_at,
            team             = req.team,
            work_notes       = req.work_notes,
            resolution_notes = req.resolution_notes,
        )
    )
    eureka_raw = data.get("eureka_moment", {})
    timeline   = [TimelineEvent(**e) for e in data.get("timeline", [])]
    return TimelineResult(
        mttr_minutes             = int(data.get("mttr_minutes", 0)),
        time_to_detect_minutes   = int(data.get("time_to_detect_minutes", 0)),
        time_to_diagnose_minutes = int(data.get("time_to_diagnose_minutes", 0)),
        time_to_fix_minutes      = int(data.get("time_to_fix_minutes", 0)),
        eureka_moment            = EurekaEvent(
            time        = eureka_raw.get("time", ""),
            description = eureka_raw.get("description", ""),
        ),
        timeline          = timeline,
        narrative_summary = data.get("narrative_summary", ""),
    )
