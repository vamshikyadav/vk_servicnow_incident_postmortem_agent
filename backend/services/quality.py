"""Stage 3 — Quality validation: score the RCA and flag gaps."""
from __future__ import annotations
from models import RCARequest, QualityResult, QualityCheck
from .gemini import call_gemini_json


PROMPT = """You are an RCA quality validation agent. Score this RCA against five criteria.

CI field: {ci}
Resolution notes:
{resolution_notes}

Work notes:
{work_notes}

Score each of these five checks:
1. resolution_detail — Does the resolution clearly explain root cause, impact, fix applied, and prevention steps? (Needs 50+ words with all four elements to pass)
2. ci_attached — Is a CMDB CI reference attached? Look for patterns like CI-XXXXX or (CMDB: ...) in the CI field
3. root_cause_identified — Is a specific root cause stated, not just symptoms or guesses?
4. prevention_mentioned — Does the resolution mention how to prevent this recurring?
5. timeline_documented — Are key timestamps present (alert time, diagnosis time, fix time)?

For each check, set severity:
  "info" if passing
  "warn" if borderline or partially met
  "fail" if clearly missing

quality_score: 0-100 (20 points per check, partial credit for warn)
overall_quality: "high" (>=80), "medium" (50-79), "low" (<50)
blocking_issues: list of strings describing critical gaps (empty if none)
recommendations: list of actionable improvement suggestions

Return ONLY valid JSON (no markdown, no backticks):
{{
  "overall_quality": "high|medium|low",
  "quality_score": 0,
  "checks": [
    {{"name": "string", "passed": true, "detail": "string", "severity": "info|warn|fail"}}
  ],
  "blocking_issues": [],
  "recommendations": []
}}"""


async def run_quality(req: RCARequest) -> QualityResult:
    data = await call_gemini_json(
        PROMPT.format(
            ci               = req.ci,
            resolution_notes = req.resolution_notes,
            work_notes       = (req.work_notes or "")[:8000],  # cap to avoid prompt overflow
        )
    )
    checks = [QualityCheck(**c) for c in data.get("checks", [])]
    return QualityResult(
        overall_quality  = data.get("overall_quality", "medium"),
        quality_score    = int(data.get("quality_score", 0)),
        checks           = checks,
        blocking_issues  = data.get("blocking_issues", []),
        recommendations  = data.get("recommendations", []),
    )
