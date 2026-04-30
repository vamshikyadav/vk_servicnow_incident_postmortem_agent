"""
Shared Pydantic models for RCA Agent REST API.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


# ── Inbound — manual text input ───────────────────────────────────

class RCARequest(BaseModel):
    incident_id:      str = Field(..., examples=["INC0091847"])
    severity:         str = Field(..., examples=["SEV2 - Major"])
    ci:               str = Field(..., examples=["payments-api (CMDB: CI-00291)"])
    opened_at:        str = Field(..., examples=["2025-06-14 02:17 UTC"])
    closed_at:        str = Field(..., examples=["2025-06-14 05:44 UTC"])
    team:             str = Field(..., examples=["Platform Reliability Engineering"])
    work_notes:       str = Field(..., description="Raw ServiceNow work notes / audit log export")
    resolution_notes: str = Field(..., description="Assignee resolution notes")

    model_config = {
        "json_schema_extra": {
            "example": {
                "incident_id":      "INC0091847",
                "severity":         "SEV2 - Major",
                "ci":               "payments-api (CMDB: CI-00291)",
                "opened_at":        "2025-06-14 02:17 UTC",
                "closed_at":        "2025-06-14 05:44 UTC",
                "team":             "Platform Reliability Engineering",
                "work_notes":       "02:17 - Alert fired...\n03:28 - Root cause found...",
                "resolution_notes": "Config rollback resolved the issue.",
            }
        }
    }


# ── Inbound — ServiceNow auto-fetch ──────────────────────────────

class SNRCARequest(BaseModel):
    """Full end-to-end: just supply the incident number."""
    incident_number: str = Field(
        ...,
        description="ServiceNow incident number",
        examples=["INC0091847"],
    )
    publish_to_confluence: bool = Field(
        default=True,
        description="Automatically create the post-mortem page in Confluence.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "incident_number":       "INC0091847",
                "publish_to_confluence": True,
            }
        }
    }


# ── Stage outputs ─────────────────────────────────────────────────

class HumanNote(BaseModel):
    time:        str
    author_type: Literal["human", "automated"]
    note:        str


class ExtractionResult(BaseModel):
    incident_id:                str
    severity:                   str
    ci_name:                    str
    ci_attached:                bool
    opened_at:                  str
    closed_at:                  str
    team:                       str
    human_notes:                list[HumanNote]
    automated_entries_filtered: int
    key_actors:                 list[str]
    affected_components:        list[str]


class EurekaEvent(BaseModel):
    time:        str
    description: str


VALID_CATEGORIES = {"detection", "investigation", "diagnosis", "fix", "recovery"}

def _coerce_category(v: str) -> str:
    """Map Gemini free-text categories to valid values."""
    v = v.lower().strip()
    if "detect" in v or "alert" in v or "monitor" in v:
        return "detection"
    if "investig" in v or "explor" in v or "check" in v or "analys" in v:
        return "investigation"
    if "diagnos" in v or "root cause" in v or "identif" in v:
        return "diagnosis"
    if "fix" in v or "remedia" in v or "resolv" in v or "rollback" in v or "deploy" in v or "patch" in v:
        return "fix"
    if "recover" in v or "restor" in v or "valid" in v or "confirm" in v:
        return "recovery"
    return "investigation"  # safe default

class TimelineEvent(BaseModel):
    time:      str
    event:     str
    category:  str = "investigation"
    is_eureka: bool = False

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        if isinstance(obj, dict) and "category" in obj:
            obj = dict(obj)
            if obj["category"] not in VALID_CATEGORIES:
                obj["category"] = _coerce_category(obj["category"])
        return super().model_validate(obj, *args, **kwargs)


class TimelineResult(BaseModel):
    mttr_minutes:             int
    time_to_detect_minutes:   int
    time_to_diagnose_minutes: int
    time_to_fix_minutes:      int
    eureka_moment:            EurekaEvent
    timeline:                 list[TimelineEvent]
    narrative_summary:        str


class QualityCheck(BaseModel):
    name:     str
    passed:   bool
    detail:   str
    severity: Literal["info", "warn", "fail"]


class QualityResult(BaseModel):
    overall_quality: Literal["high", "medium", "low"]
    quality_score:   int = Field(..., ge=0, le=100)
    checks:          list[QualityCheck]
    blocking_issues: list[str]
    recommendations: list[str]


class ActionItem(BaseModel):
    owner: str
    task:  str
    due:   str


class ConfluenceSection(BaseModel):
    heading: str
    content: str


class ConfluenceResult(BaseModel):
    page_title:   str
    sections:     list[ConfluenceSection]
    action_items: list[ActionItem]
    tags:         list[str]


class ConfluencePublishResult(BaseModel):
    page_id:   str
    page_url:  str
    title:     str
    space_key: str


class SNFetchResult(BaseModel):
    incident_id:    str
    sys_id:         str
    severity:       str
    ci:             str
    opened_at:      str
    closed_at:      str
    team:           str
    short_desc:     str
    work_notes_raw: str
    audit_count:    int


class RCAResponse(BaseModel):
    incident_id:               str
    status:                    Literal["success", "partial", "failed"] = "success"
    servicenow_fetch:          SNFetchResult           | None = None
    extraction:                ExtractionResult        | None = None
    timeline:                  TimelineResult          | None = None
    quality:                   QualityResult           | None = None
    confluence:                ConfluenceResult        | None = None
    confluence_page_published: ConfluencePublishResult | None = None
    errors:                    dict[str, str]          = {}
