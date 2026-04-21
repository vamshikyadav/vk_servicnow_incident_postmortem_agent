"""
Shared Pydantic models for RCA Agent REST API.
These are the schemas external consumers (and the frontend) send and receive.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


# ── Inbound ─────────────────────────────────────────────────────────────────

class RCARequest(BaseModel):
    incident_id: str = Field(..., examples=["INC0091847"])
    severity: str = Field(..., examples=["SEV2 - Major"])
    ci: str = Field(..., description="CI name + CMDB reference", examples=["payments-api (CMDB: CI-00291)"])
    opened_at: str = Field(..., examples=["2025-06-14 02:17 UTC"])
    closed_at: str = Field(..., examples=["2025-06-14 05:44 UTC"])
    team: str = Field(..., examples=["Platform Reliability Engineering"])
    work_notes: str = Field(..., description="Raw ServiceNow work notes / audit log export")
    resolution_notes: str = Field(..., description="Assignee resolution notes")

    model_config = {
        "json_schema_extra": {
            "example": {
                "incident_id": "INC0091847",
                "severity": "SEV2 - Major",
                "ci": "payments-api (CMDB: CI-00291)",
                "opened_at": "2025-06-14 02:17 UTC",
                "closed_at": "2025-06-14 05:44 UTC",
                "team": "Platform Reliability Engineering",
                "work_notes": "02:17 - Alert fired: payment gateway timeout rate > 15%\n02:21 - On-call paged\n03:28 - Config change found at 01:55 UTC reduced max_connections from 200 to 20\n03:31 - Config rollback initiated",
                "resolution_notes": "Root cause: misconfigured max_connections in payments-api. Rolled back at 03:31 UTC. Prevention: add CI/CD validation step."
            }
        }
    }


# ── Stage outputs ────────────────────────────────────────────────────────────

class HumanNote(BaseModel):
    time: str
    author_type: Literal["human", "automated"]
    note: str


class ExtractionResult(BaseModel):
    incident_id: str
    severity: str
    ci_name: str
    ci_attached: bool
    opened_at: str
    closed_at: str
    team: str
    human_notes: list[HumanNote]
    automated_entries_filtered: int
    key_actors: list[str]
    affected_components: list[str]


class EurekaEvent(BaseModel):
    time: str
    description: str


class TimelineEvent(BaseModel):
    time: str
    event: str
    category: Literal["detection", "investigation", "diagnosis", "fix", "recovery"]
    is_eureka: bool = False


class TimelineResult(BaseModel):
    mttr_minutes: int
    time_to_detect_minutes: int
    time_to_diagnose_minutes: int
    time_to_fix_minutes: int
    eureka_moment: EurekaEvent
    timeline: list[TimelineEvent]
    narrative_summary: str


class QualityCheck(BaseModel):
    name: str
    passed: bool
    detail: str
    severity: Literal["info", "warn", "fail"]


class QualityResult(BaseModel):
    overall_quality: Literal["high", "medium", "low"]
    quality_score: int = Field(..., ge=0, le=100)
    checks: list[QualityCheck]
    blocking_issues: list[str]
    recommendations: list[str]


class ActionItem(BaseModel):
    owner: str
    task: str
    due: str


class ConfluenceSection(BaseModel):
    heading: str
    content: str


class ConfluenceResult(BaseModel):
    page_title: str
    sections: list[ConfluenceSection]
    action_items: list[ActionItem]
    tags: list[str]


# ── Full pipeline response ────────────────────────────────────────────────────

class RCAResponse(BaseModel):
    incident_id: str
    status: Literal["success", "partial", "failed"] = "success"
    extraction: ExtractionResult | None = None
    timeline: TimelineResult | None = None
    quality: QualityResult | None = None
    confluence: ConfluenceResult | None = None
    errors: dict[str, str] = {}


# ── Individual stage request (for partial calls) ─────────────────────────────

class StageRequest(BaseModel):
    """Used when a consumer only wants to run one specific stage."""
    request: RCARequest
    stage: Literal["extraction", "timeline", "quality", "confluence"]
